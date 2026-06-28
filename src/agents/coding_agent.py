"""
N-01b 相当: ソースコードを分析して実装計画を生成する ADK LlmAgent。

Vertex AI バックエンド: 環境変数 GOOGLE_GENAI_USE_VERTEXAI=1 で自動有効化。
output_schema により ADK が Gemini Structured Outputs を自動設定し、型安全な応答を保証する。
"""
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.config import GEMINI_MODEL
from src.schemas.plan import FileChange, GenerationResult

_APP_NAME = "rtg-coding-agent"
_OUTPUT_KEY = "result"

_session_svc = InMemorySessionService()

agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="ソースコードを分析し、変更要求に対する実装計画を生成するコーディングエージェント",
    instruction=(
        "あなたはシニアソフトウェアエンジニアです。\n"
        "対象コードベースのファイル内容と、ユーザーの変更要求を受け取り、"
        "実装に必要なファイル変更とコマンドを生成してください。\n\n"
        "## file_changes\n"
        "- path: コードベース内の相対ファイルパス\n"
        "- description: 変更内容の説明\n"
        "- content: 変更後のファイル全体の内容（新規・小規模変更の場合）\n"
        "- diff: unified diff 形式（既存ファイルへの部分変更で content が大きくなる場合）\n"
        "content と diff はどちらか一方のみ設定すること。\n\n"
        "## commands\n"
        "実行順に記載すること（マイグレーション → テスト → ビルド の順が基本）。\n\n"
        "## explanation\n"
        "実装方針を 1〜3 文で簡潔に説明すること。\n\n"
        "コードベースが提供されない場合は、変更要求の内容から一般的な実装計画を立案すること。"
    ),
    output_schema=GenerationResult,
    output_key=_OUTPUT_KEY,
)

_runner = Runner(agent=agent, session_service=_session_svc, app_name=_APP_NAME)


async def generate(
    input_text: str,
    code_context: str = "",
    target_source: str = "",
) -> GenerationResult:
    """ソースコード文脈と変更要求から GenerationResult を生成して返す。"""
    session = await _session_svc.create_session(app_name=_APP_NAME, user_id="system")

    context_section = (
        f"\n\n## 対象コードベース（{target_source}）\n\n{code_context[:30_000]}"
        if code_context
        else ""
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=(
            f"## 変更要求\n{input_text}"
            f"{context_section}"
        ))],
    )

    async for _ in _runner.run_async(
        user_id="system",
        session_id=session.id,
        new_message=message,
    ):
        pass

    updated = await _session_svc.get_session(
        app_name=_APP_NAME, user_id="system", session_id=session.id
    )
    result_dict = updated.state.get(_OUTPUT_KEY)
    if not result_dict:
        raise ValueError("coding_agent からの応答が空でした")

    return GenerationResult.model_validate(result_dict)
