"""
RTG コーディングエージェント (A2A 対応版)。

RTG 本体から受け取った質問テキストを Vertex AI (Gemini) に投げ、
テキスト回答を返す。output_schema は使用しない（プレーンテキスト応答が必要なため）。
回答は run_async イベントのテキストパーツを収集して組み立てる。

GCS 上の対象アプリコードは一括プロンプト注入ではなく、LlmAgent に登録した
探索ツール（src/agents/tools.py）を通じて LLM が自律的に読みに行く方式を採る。
対象アプリの project_id はセッション状態 (state["project_id"]) 経由でツールに渡す。
"""
import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.tools import (
    list_project_files,
    read_project_file,
    search_project_code,
)
from src.config import GEMINI_MODEL

_APP_NAME = "rtg-coding-agent"
_LOCAL_TIMEOUT = 120.0  # 複数回のツール呼び出し（探索→読み込み→回答）を許容するため 60→120 秒に変更

_INSTRUCTION = (
    "あなたはシニアソフトウェアエンジニアです。"
    "受け取った指示がどのような種別であっても、回答は必ず次の2形式のうち"
    "いずれか一方のみで返してください。それ以外の形式（説明文・確認応答・箇条書きの候補列挙等）"
    "では絶対に回答しないこと。\n\n"
    "## 探索方針\n"
    "この方針は、spec作成・編集・影響調査・ユースケース候補提示など、対象アプリの実際の"
    "コードを分析する必要がある指示にのみ適用する。該当する場合は、推測で回答せず、まず"
    "list_project_files で全体像を掴み、read_project_file / search_project_code で"
    "関連コードを確認してから回答すること。対象アプリが指定されていない（ツールが"
    "「指定されていない」旨を返す）場合は、ツールを使わず一般的な方針として回答すること。"
    "コマンド列挙・模擬実行結果の報告・拒否確認では、これらのツールを使う必要はない"
    "（既に与えられた情報だけでテキストを組み立てればよい）。\n\n"
    "## ツール名と出力の区別（重要）\n"
    "list_project_files / read_project_file / search_project_code は、あなたが内部的に"
    "コード分析のために呼び出す手段であり、ユーザーへの回答内容ではない。これらのツール名や"
    "呼び出し構文（例: list_project_files() のような記述）を回答テキストにそのまま"
    "含めてはならない。\n\n"
    "## 実行可否について（重要）\n"
    "あなたは実際にコマンドを実行する主体ではなく、常にテキストで回答するだけの役割である。"
    "「実行権限がない」「ツールの機能範囲外である」等を理由に、コマンド列や spec の生成を"
    "拒否したり、要求と異なる形式（能力の限界説明など）で回答したりしてはならない。たとえ"
    "実際には実行できない操作であっても、求められた形式（spec または commands）で淡々と"
    "内容を組み立てて回答すること。\n\n"
    "## 出力形式（必ずこの2つのいずれか一方）\n"
    "### 形式A: spec\n"
    "Markdown 形式。## 実現方針 / ## 変更範囲 / ## 手順 の3セクション構成。\n"
    "### 形式B: commands\n"
    "1行1コマンド・コマンドのみ（説明・番号・コードフェンス不要）。ここでいうコマンドとは、"
    "対象システムに対して実行される一般的なシェル/デプロイ/DB/テストコマンド"
    "（例: git, npm, alembic, pytest, SQL文など）を指し、あなた自身の探索ツール呼び出しとは"
    "無関係である。\n\n"
    "## 形式の選び方\n"
    "受け取った指示が「実行すべきコマンドの列挙」または「承認されたコマンドの模擬実行」を"
    "求めるものである場合は形式B(commands)を返すこと。それ以外の指示（spec作成・編集の依頼、"
    "影響調査、拒否通知への応答、ユースケース候補の提示など）はすべて形式A(spec)で返すこと。"
    "判断に迷う場合は形式A(spec)を選ぶこと。\n\n"
    "コードブロック（```）で全体を囲まないこと。"
)

_session_svc = InMemorySessionService()

_agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="RTG の指示に従い、spec 全文またはコマンド列のいずれかを生成するコーディングエージェント",
    instruction=_INSTRUCTION,
    tools=[list_project_files, read_project_file, search_project_code],
)

_runner = Runner(agent=_agent, session_service=_session_svc, app_name=_APP_NAME)


async def run_query(question: str, project_id: str | None = None) -> str:
    """
    LLM に質問を投げてテキスト回答を返す。タイムアウト時は ValueError を送出。

    project_id を渡すと、セッション状態経由で探索ツール（list_project_files 等）が
    該当プロジェクトの GCS コードを参照できるようになる。None の場合、ツールは
    「対象アプリが指定されていない」旨を返し、LLM は一般論で回答する。
    """
    session = await _session_svc.create_session(
        app_name=_APP_NAME,
        user_id="system",
        state={"project_id": project_id},
    )
    message = types.Content(role="user", parts=[types.Part(text=question)])

    collected: list[str] = []

    try:
        async with asyncio.timeout(_LOCAL_TIMEOUT):
            async for event in _runner.run_async(
                user_id="system",
                session_id=session.id,
                new_message=message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            collected.append(part.text)
    except TimeoutError as exc:
        raise ValueError(f"エージェントがタイムアウトしました（{_LOCAL_TIMEOUT}秒）") from exc

    if not collected:
        raise ValueError("エージェントからの応答が空でした")

    return "".join(collected)
