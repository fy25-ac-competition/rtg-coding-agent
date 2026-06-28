"""
POST /generate エンドポイントのテスト。
GCS・Firestore・ADK エージェントをモックして、ルーターの振る舞いのみを検証する。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.schemas.plan import FileChange, GenerationResult

client = TestClient(app)

_MOCK_RESULT = GenerationResult(
    explanation="Product モデルに stock_reserved フィールドを追加します。",
    file_changes=[
        FileChange(
            path="src/models/product.py",
            description="stock_reserved フィールドを追加",
            content="class Product:\n    stock_reserved: int = 0\n",
        )
    ],
    commands=["alembic revision --autogenerate -m 'add_stock_reserved'", "pytest tests/"],
)


@patch("app.routers.generate.agent_generate", new_callable=AsyncMock, return_value=_MOCK_RESULT)
def test_generate_with_direct_context(mock_agent):
    """target_context を直接渡した場合、GCS/Firestore を呼ばずにエージェントが実行される。"""
    resp = client.post("/generate", json={
        "input_text": "stock_reserved カラムを追加したい",
        "target_context": "class Product:\n    stock: int = 0\n",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["explanation"] == _MOCK_RESULT.explanation
    assert len(body["file_changes"]) == 1
    assert len(body["commands"]) == 2
    mock_agent.assert_called_once()


@patch("app.routers.generate.agent_generate", new_callable=AsyncMock, return_value=_MOCK_RESULT)
@patch("app.routers.generate.gcs_client.load_project_context", return_value="# mock context")
@patch("app.routers.generate.firestore_client.get_project", return_value=None)
def test_generate_with_gcs_source(mock_fs, mock_gcs, mock_agent):
    """target_source=gcs:<id> のとき GCS からコード文脈を取得してエージェントを呼ぶ。"""
    resp = client.post("/generate", json={
        "input_text": "stock_reserved カラムを追加したい",
        "target_source": "gcs:mori-market",
    })
    assert resp.status_code == 200
    mock_gcs.assert_called_once_with("mori-market")
    mock_agent.assert_called_once()


@patch("app.routers.generate.agent_generate", new_callable=AsyncMock, side_effect=Exception("LLM error"))
def test_generate_agent_error(mock_agent):
    """エージェントが例外を投げた場合、500 を返す。"""
    resp = client.post("/generate", json={"input_text": "テスト"})
    assert resp.status_code == 500
