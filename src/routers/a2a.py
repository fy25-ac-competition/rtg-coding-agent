"""
A2A JSON-RPC 2.0 エンドポイント。

RTG 本体の A2ACodingAgentClient が送信するリクエストを受け取り、
Vertex AI (Gemini) の回答を A2A レスポンス形式で返す。

リクエスト: POST /
  - method: "message/send"
  - params.message.parts[0].text: 質問テキスト（RTG 側テンプレートで組み立て済み）
  - params.message.metadata.target_source: 対象アプリ識別子（オプション、debug-20260705 §4）

レスポンス: result.artifacts[0].parts[0].text に回答テキストを格納
"""
import logging

from fastapi import APIRouter, HTTPException

from src.agents.coding_agent import run_query
from src.schemas.a2a import A2ARequest, A2AResponse
from src.services.gcs_client import load_project_context_for_source

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=A2AResponse)
async def a2a_endpoint(body: A2ARequest) -> A2AResponse:
    """RTG からの A2A JSON-RPC 2.0 リクエストを処理する。"""
    if body.method != "message/send":
        raise HTTPException(status_code=400, detail=f"未対応の method: {body.method}")

    parts = body.params.message.parts
    if not parts or not parts[0].text:
        raise HTTPException(status_code=400, detail="params.message.parts が空です")

    question = parts[0].text

    # metadata.target_source から対象アプリ識別子を取得（オプション）
    target_source: str | None = None
    if body.params.message.metadata:
        target_source = body.params.message.metadata.get("target_source")

    # GCS からコード文脈を取得して質問に付加する（demo: ソース対応）
    code_context = load_project_context_for_source(target_source)
    if code_context:
        question = (
            question
            + f"\n\n## 対象アプリ（{target_source}）のコード文脈\n\n"
            + code_context
        )
        logger.info("target_source=%s のコード文脈を付加しました", target_source)

    try:
        answer = await run_query(question)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("エージェント実行エラー: %s", exc)
        raise HTTPException(status_code=502, detail=f"エージェントエラー: {exc}") from exc

    return A2AResponse.from_text(answer)
