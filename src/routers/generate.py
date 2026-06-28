from fastapi import APIRouter, HTTPException

from src.agents.coding_agent import generate as agent_generate
from src.schemas.plan import GenerationRequest, GenerationResult
from src.services import gcs_client, firestore_client

router = APIRouter()


def _resolve_context(req: GenerationRequest) -> tuple[str, str]:
    """コード文脈と実際の target_source 文字列を返す。"""
    if req.target_context:
        return req.target_context, req.target_source

    if req.target_source.startswith("gcs:"):
        project_id = req.target_source[4:]
        meta = firestore_client.get_project(project_id)
        context = gcs_client.load_project_context(project_id)
        return context, req.target_source

    return "", req.target_source


@router.post("/generate", response_model=GenerationResult)
async def generate(body: GenerationRequest) -> GenerationResult:
    """ソースコードを分析して実装計画を生成する。"""
    try:
        code_context, target_source = _resolve_context(body)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"コード文脈の取得に失敗しました: {e}")

    try:
        return await agent_generate(body.input_text, code_context, target_source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エージェントの実行に失敗しました: {e}")
