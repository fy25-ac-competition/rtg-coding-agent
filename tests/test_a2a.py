"""
POST / A2A エンドポイントのテスト。
ADK エージェント・GCS をモックして、ルーターの振る舞いのみを検証する。
"""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# google.* 未インストール環境でも import を通せるよう事前スタブ
# "google.adk.tools" は src/agents/tools.py の ToolContext import に必要なため追加。
for _mod in (
    "google", "google.adk", "google.adk.agents", "google.adk.runners",
    "google.adk.sessions", "google.adk.tools", "google.genai", "google.genai.types",
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
def test_a2a_spec_creation(mock_run):
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
def test_a2a_command_list(mock_run):
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


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="spec text with project context")
def test_a2a_with_target_source_metadata(mock_run):
    """
    metadata.target_source が渡された場合、target_source から project_id を
    解決し run_query(question, project_id=...) を呼ぶ（GCS 探索はツール側が担う）。
    """
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
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0].startswith("以下の要望を実現する")
    assert mock_run.call_args.kwargs.get("project_id") == "system-m"


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="了解しました。実行しません。")
def test_a2a_notify_rejection(mock_run):
    """拒否通知リクエストが処理される（調整後は spec 形式のテキストが返る想定。
    ここでは run_query を mock 化しているため mock 値をそのまま検証するのみ）。"""
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
def test_a2a_suggest_usecases(mock_run):
    """ユースケース候補生成リクエストが処理される（調整後は spec 形式のテキストが返る想定。
    ここでは run_query を mock 化しているため mock 値をそのまま検証するのみ）。
    target_source があれば project_id が渡る。"""
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
    assert mock_run.call_args.kwargs.get("project_id") == "system-m"


def test_a2a_no_target_source_means_no_project_id():
    """metadata が無い/target_source が無い場合、project_id=None で run_query が呼ばれる。"""
    with patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="ok") as mock_run:
        resp = client.post("/", json=_BASE_MSG)
        assert resp.status_code == 200
        assert mock_run.call_args.kwargs.get("project_id") is None


def test_a2a_non_demo_target_source_means_no_project_id():
    """target_source が demo: 以外（例: github:）の場合、project_id=None になる。"""
    msg = dict(_BASE_MSG)
    msg["params"]["message"]["metadata"] = {"target_source": "github:https://example.com/repo"}
    with patch("src.routers.a2a.run_query", new_callable=AsyncMock, return_value="ok") as mock_run:
        resp = client.post("/", json=msg)
        assert resp.status_code == 200
        assert mock_run.call_args.kwargs.get("project_id") is None


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
def test_a2a_agent_timeout(mock_run):
    """エージェントが ValueError を投げた場合 500 を返す。"""
    resp = client.post("/", json=_BASE_MSG)
    assert resp.status_code == 500
    assert "タイムアウト" in resp.json()["detail"]


@patch("src.routers.a2a.run_query", new_callable=AsyncMock, side_effect=Exception("LLM 障害"))
def test_a2a_agent_unexpected_error(mock_run):
    """エージェントが予期せぬ例外を投げた場合 502 を返す。"""
    resp = client.post("/", json=_BASE_MSG)
    assert resp.status_code == 502
