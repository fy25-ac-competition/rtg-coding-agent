"""
RTG コーディングエージェント (A2A 対応版)。

RTG 本体から受け取った質問テキストを Vertex AI (Gemini) に投げ、
テキスト回答を返す。output_schema は使用しない（プレーンテキスト応答が必要なため）。
回答は run_async イベントのテキストパーツを収集して組み立てる。
"""
import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.config import GEMINI_MODEL

_APP_NAME = "rtg-coding-agent"
_LOCAL_TIMEOUT = 60.0

_session_svc = InMemorySessionService()

_agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="RTG の指示に従い spec 作成・コマンド生成・影響調査等を行うコーディングエージェント",
    instruction=(
        "あなたはシニアソフトウェアエンジニアです。"
        "受け取った指示の種別に応じた回答をテキストのみで返してください。\n\n"
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
)

_runner = Runner(agent=_agent, session_service=_session_svc, app_name=_APP_NAME)


async def run_query(question: str) -> str:
    """LLM に質問を投げてテキスト回答を返す。タイムアウト時は ValueError を送出。"""
    session = await _session_svc.create_session(app_name=_APP_NAME, user_id="system")
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
