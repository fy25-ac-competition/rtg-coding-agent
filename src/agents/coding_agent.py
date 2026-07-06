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

_session_svc = InMemorySessionService()

_agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="RTG の指示に従い spec 作成・コマンド生成・影響調査等を行うコーディングエージェント",
    instruction=(
        "あなたはシニアソフトウェアエンジニアです。"
        "受け取った指示の種別に応じた回答をテキストのみで返してください。\n\n"
        "## 探索方針\n"
        "対象アプリのコードに関わる指示（spec 作成・影響調査・ユースケース候補等）では、"
        "推測で回答せず、まず list_project_files で全体像を掴み、read_project_file / "
        "search_project_code で関連コードを確認してから回答すること。"
        "対象アプリが指定されていない（ツールが「指定されていない」旨を返す）場合は、"
        "ツールを使わず一般的な方針として回答すること。\n\n"
        "## 回答スタイル（指示種別ごと）\n"
        "- spec 作成・更新: Markdown 形式。"
        "## 実現方針 / ## 変更範囲 / ## 手順 の3セクション構成を推奨。\n"
        "- コマンドリスト生成: 1行1コマンド・コマンドのみ（説明・番号・コードフェンス不要）。\n"
        "- 影響調査: 影響範囲・関連コード名・変更箇所を含めた簡潔な日本語報告文。\n"
        "- 模擬実行結果: 実際のシステムには変更を加えない前提で結果を日本語で報告。\n"
        "- 拒否通知: 「了解しました。実行しません。」等の簡潔な確認文。\n"
        "- ユースケース候補: 「〜したい」形式で1行1件、2〜3件列挙。\n"
        "コードブロック（```）で全体を囲まないこと。"
    ),
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
