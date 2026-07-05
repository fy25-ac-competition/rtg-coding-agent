"""
POST / A2A エンドポイントのテスト。
ADK エージェント・GCS をモックして、ルーターの振る舞いのみを検証する。
"""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# google.* 未インストール環境でも import を通せるよう事前スタブ
for _mod in (
    "google", "google.adk", "google.adk.agents", "google.adk.runners",
    "google.adk.sessions", "google.genai", "google.genai.types",
    "google.cloud", "google.cloud.storage",
):
    sys.modules.setdefault(_mod, MagicMock())

from src.main import app  # noqa: E402

client = TestClient(app)

# ---------------------------------------------------------------------------
# 共通ペイロード
# ---------------------------------------------------------------------------

_BASE_MSG = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [{"text": "以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\nカート画面にクーポン機能を追加したい"}]
        }
    }
}


# ---------------------------------------------------------------------------
# 正常系
# ---------------------------------------------------------------------------

@patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="# spec\n\n## 実現方針\nクーポン機能を追加する。")
@patch("src.routers.a2a.load_project_context_for_source", return_value="")
def test_a2a_spec_creation(mock_gcs, mock_run):
    """spec 作成リクエストが A2A 形式で正しく処理される。"""
    resp = client.post("/", json=_BASE_MSG)

    assert resp.status_code == 200
    body = resp.json()
    assert "result" in body
    artifacts = body["result"]["artifacts"]
    assert len(artifacts) == 1
    assert artifacts[0]["parts"][0]["text"] == "# spec\n\n## 実現方針\nクーポン機能を追加する。"
    mock_run.assert_called_once()


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="git checkout -b feature/coupon\nvim cart.html")
@patch("src.routers.a2a.load_project_context_for_source", return_value="")
def test_a2a_command_list(mock_gcs, mock_run):
    """コマンドリスト生成リクエストが処理される。"""
    msg = dict(_BASE_MSG)
    msg["params"] = {
        "message": {
            "role": "user",
            "parts": [{"text": "以下の spec を実現するために実行すべきコマンドを、実行順に列挙してください。\n--- spec ---\n# spec: クーポン機能\n..."}]
        }
    }
    resp = client.post("/", json=msg)

    assert resp.status_code == 200
    text = resp.json()["result"]["artifacts"][0]["parts"][0]["text"]
    assert "git checkout" in text


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="spec text with target context")
@patch("src.routers.a2a.load_project_context_for_source", return_value="### index.html\n```\n<html>...</html>\n```")
def test_a2a_with_target_source_metadata(mock_gcs, mock_run):
    """metadata.target_source が渡された場合、GCS コード文脈を付加して呼ぶ。"""
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\n在庫を減らしたい"}],
                "metadata": {"target_source": "demo:system-m"}
            }
        }
    }
    resp = client.post("/", json=msg)

    assert resp.status_code == 200
    mock_gcs.assert_called_once_with("demo:system-m")
    # GCS 文脈が question に付加されていることをエージェント呼び出し引数で確認
    call_arg = mock_run.call_args.args[0]
    assert "対象アプリ（demo:system-m）のコード文脈" in call_arg
    assert "index.html" in call_arg


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="了解しました。実行しません。")
@patch("src.routers.a2a.load_project_context_for_source", return_value="")
def test_a2a_notify_rejection(mock_gcs, mock_run):
    """拒否通知リクエストが処理される。"""
    msg = dict(_BASE_MSG)
    msg["params"] = {
        "message": {
            "role": "user",
            "parts": [{"text": "以下のコマンドは拒否されました。実行しないでください。\n--- コマンド ---\ngit push --force"}]
        }
    }
    resp = client.post("/", json=msg)
    assert resp.status_code == 200


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="候補1\n候補2\n候補3")
@patch("src.routers.a2a.load_project_context_for_source", return_value="")
def test_a2a_suggest_usecases(mock_gcs, mock_run):
    """ユースケース候補生成リクエストが処理される。"""
    msg = dict(_BASE_MSG)
    msg["params"] = {
        "message": {
            "role": "user",
            "parts": [{"text": "以下の対象ソースを分析し、ユーザーが「変更したいこと」の候補を2〜3件、1行1件で列挙してください。\n--- 対象ソース ---\ndemo:system-m"}],
            "metadata": {"target_source": "demo:system-m"}
        }
    }
    resp = client.post("/", json=msg)
    assert resp.status_code == 200
    text = resp.json()["result"]["artifacts"][0]["parts"][0]["text"]
    assert "候補1" in text


# ---------------------------------------------------------------------------
# 異常系
# ---------------------------------------------------------------------------

def test_a2a_invalid_method():
    """method が message/send 以外の場合は 400 を返す。"""
    body = dict(_BASE_MSG)
    body["method"] = "unknown/method"
    resp = client.post("/", json=body)
    assert resp.status_code == 400
    assert "未対応の method" in resp.json()["detail"]


def test_a2a_empty_parts():
    """parts が空の場合は 400 を返す。"""
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {"message": {"role": "user", "parts": []}}
    }
    resp = client.post("/", json=body)
    assert resp.status_code == 400


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, side_effect=ValueError("タイムアウト"))
@patch("src.routers.a2a.load_project_context_for_source", return_value="")
def test_a2a_agent_timeout(mock_gcs, mock_run):
    """エージェントが ValueError を投げた場合 500 を返す。"""
    resp = client.post("/", json=_BASE_MSG)
    assert resp.status_code == 500
    assert "タイムアウト" in resp.json()["detail"]


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, side_effect=Exception("LLM 障害"))
@patch("src.routers.a2a.load_project_context_for_source", return_value="")
def test_a2a_agent_unexpected_error(mock_gcs, mock_run):
    """エージェントが予期せぬ例外を投げた場合 502 を返す。"""
    resp = client.post("/", json=_BASE_MSG)
    assert resp.status_code == 502
