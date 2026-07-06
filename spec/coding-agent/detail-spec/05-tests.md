# 編集単位 5: tests/test_a2a.py（改修）+ tests/test_tools.py（新規）

**依存**: [01-gcs-client.md](01-gcs-client.md)〜[04-a2a-router.md](04-a2a-router.md) すべて完了後
（実装全体の挙動を検証するテストのため、最後に着手する）

---

## 1. 対象ファイル / 変更種別

- `tests/test_a2a.py` — 改修（一括注入前提のパッチを除去し、project_id 解決の検証に置き換え）
- `tests/test_tools.py` — 新規（`gcs_client` の探索プリミティブ 3 種を検証）

---

## 2. tests/test_a2a.py

### 2.1 現状（Before）

2026-07-06 時点の全文（176行）:

```python
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
            "parts": [{"text": "以下の要望を実現する spec ファイル(Markdown・実現方針/変更範囲/手順)を作成してください:\nカート画面にクーポン機能を追加したい"}]
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
                "parts": [{"text": "以下の要望を実現する spec ファイル(Markdown・実現方針/変更範囲/手順)を作成してください:\n在庫を減らしたい"}],
                "metadata": {"target_source": "demo:system-m"}
            }
        }
    }
    resp = client.post("/", json=msg)

    assert resp.status_code == 200
    mock_gcs.assert_called_once_with("demo:system-m")
    # GCS 文脈が question に付加されていることをエージェント呼び出し引数で確認
    call_arg = mock_run.call_args.args[0]
    assert "対象アプリ(demo:system-m)のコード文脈" in call_arg
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
```

乖離チェック済み（[00-overview.md §4](00-overview.md#4-乖離チェック結果実ソース-vs-本-spec2026-07-06-時点)）。

### 2.2 変更後（After）：完全なファイル全文

```python
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
            "parts": [{"text": "以下の要望を実現する spec ファイル(Markdown・実現方針/変更範囲/手順)を作成してください:\nカート画面にクーポン機能を追加したい"}]
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
    解決し run_query(question, project_id=...) を呼ぶ(GCS 探索はツール側が担う)。
    """
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"text": "以下の要望を実現する spec ファイル(Markdown・実現方針/変更範囲/手順)を作成してください:\n在庫を減らしたい"}],
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
def test_a2a_suggest_usecases(mock_run):
    """ユースケース候補生成リクエストが処理される。target_source があれば project_id が渡る。"""
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
    """target_source が demo: 以外(例: github:)の場合、project_id=None になる。"""
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
```

### 2.3 差分の要点

- 事前スタブ一覧に `"google.adk.tools"` を追加（`src/agents/tools.py` の
  `from google.adk.tools import ToolContext` を通すため。`from src.main import app` の
  import チェーンが `coding_agent.py` → `agents/tools.py` → `google.adk.tools` まで辿るため必須）。
- 全テストから `@patch("src.routers.a2a.load_project_context_for_source", ...)` を削除
  （関数自体が [01-gcs-client.md](01-gcs-client.md) で削除されるため、patch 対象が存在しなくなる）。
- `test_a2a_with_target_source_metadata`: 「GCS 文脈が question に連結される」検証から
  「`run_query` が `project_id="system-m"` 付きで呼ばれる」検証に書き換え。
- `test_a2a_suggest_usecases`: 同様に `load_project_context_for_source` パッチを外し、
  `project_id` が渡ることを追加検証。
- **新規テスト 2 件を追加**:
  - `test_a2a_no_target_source_means_no_project_id`
  - `test_a2a_non_demo_target_source_means_no_project_id`
  （[04-a2a-router.md §6](04-a2a-router.md) のエッジケースをカバーするため）

---

## 3. tests/test_tools.py（新規）

### 3.1 現状（Before）

存在しない（新規ファイル）。

### 3.2 変更後（After）：完全なファイル全文

```python
"""
src/services/gcs_client.py の探索プリミティブ（list_files / read_file / search_code）のテスト。
google.cloud.storage をモックし、GCS への実アクセスなしで検証する。
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# google.* 未インストール環境でも import を通せるよう事前スタブ
for _mod in ("google", "google.cloud", "google.cloud.storage"):
    sys.modules.setdefault(_mod, MagicMock())

from src.services import gcs_client  # noqa: E402


def _make_blob(name: str, size: int = 100, text: str = "dummy"):
    blob = MagicMock()
    blob.name = name
    blob.size = size
    blob.download_as_text.return_value = text
    blob.exists.return_value = True
    return blob


# ---------------------------------------------------------------------------
# list_files
# ---------------------------------------------------------------------------

def test_list_files_excludes_skip_extensions():
    """スキップ対象拡張子（.png, .pyc 等）は一覧から除外される。"""
    blobs = [
        _make_blob("proj/app.py"),
        _make_blob("proj/logo.png"),
        _make_blob("proj/module.pyc"),
        _make_blob("proj/README.md"),
    ]
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"), \
         patch("src.services.gcs_client.storage.Client") as mock_client_cls:
        mock_client_cls.return_value.list_blobs.return_value = blobs
        result = gcs_client.list_files("proj")

    assert result == ["app.py", "README.md"]


def test_list_files_empty_bucket_config_returns_empty():
    """GCS_BUCKET 未設定時は空リストを返す。"""
    with patch("src.services.gcs_client.GCS_BUCKET", ""):
        assert gcs_client.list_files("proj") == []


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

def test_read_file_returns_content():
    """正常系: 指定パスの内容が返る。"""
    blob = _make_blob("proj/app.py", size=100, text="print('hello')")
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"), \
         patch("src.services.gcs_client.storage.Client") as mock_client_cls:
        mock_client_cls.return_value.bucket.return_value.blob.return_value = blob
        result = gcs_client.read_file("proj", "app.py")

    assert result == "print('hello')"


def test_read_file_not_found():
    """不存在の場合はエラー文字列を返す（例外は投げない）。"""
    blob = _make_blob("proj/missing.py")
    blob.exists.return_value = False
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"), \
         patch("src.services.gcs_client.storage.Client") as mock_client_cls:
        mock_client_cls.return_value.bucket.return_value.blob.return_value = blob
        result = gcs_client.read_file("proj", "missing.py")

    assert "ファイルが見つかりません" in result


def test_read_file_too_large():
    """50KB 超のファイルはエラー文字列を返す。"""
    blob = _make_blob("proj/big.py", size=60_000)
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"), \
         patch("src.services.gcs_client.storage.Client") as mock_client_cls:
        mock_client_cls.return_value.bucket.return_value.blob.return_value = blob
        result = gcs_client.read_file("proj", "big.py")

    assert "ファイルが大きすぎます" in result


def test_read_file_bucket_unset():
    """GCS_BUCKET 未設定時はエラー文字列を返す。"""
    with patch("src.services.gcs_client.GCS_BUCKET", ""):
        result = gcs_client.read_file("proj", "app.py")
    assert "GCS_BUCKET が未設定" in result


# ---------------------------------------------------------------------------
# search_code
# ---------------------------------------------------------------------------

def test_search_code_returns_matching_lines():
    """マッチ行が "path:lineno: 内容" 形式で返る。"""
    blob = _make_blob("proj/app.py", size=100, text="import os\ndef foo():\n    return os.getcwd()\n")
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"), \
         patch("src.services.gcs_client.storage.Client") as mock_client_cls:
        mock_client_cls.return_value.list_blobs.return_value = [blob]
        result = gcs_client.search_code("proj", r"os\.")

    assert result == ["app.py:1: import os", "app.py:3: return os.getcwd()"]


def test_search_code_invalid_regex_returns_error_entry():
    """不正な正規表現の場合、例外を投げずエラー文字列 1 件のリストを返す。"""
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"):
        result = gcs_client.search_code("proj", "[")

    assert len(result) == 1
    assert "正規表現が不正です" in result[0]


def test_search_code_respects_max_hits():
    """マッチ件数が _MAX_SEARCH_HITS を超えない。"""
    many_lines = "\n".join(f"match {i}" for i in range(gcs_client._MAX_SEARCH_HITS + 20))
    blob = _make_blob("proj/big.txt", size=100, text=many_lines)
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"), \
         patch("src.services.gcs_client.storage.Client") as mock_client_cls:
        mock_client_cls.return_value.list_blobs.return_value = [blob]
        result = gcs_client.search_code("proj", "match")

    assert len(result) == gcs_client._MAX_SEARCH_HITS


def test_search_code_skips_oversized_files():
    """50KB 超のファイルは検索対象から除外される。"""
    blob = _make_blob("proj/huge.py", size=60_000, text="target_pattern")
    with patch("src.services.gcs_client.GCS_BUCKET", "test-bucket"), \
         patch("src.services.gcs_client.storage.Client") as mock_client_cls:
        mock_client_cls.return_value.list_blobs.return_value = [blob]
        result = gcs_client.search_code("proj", "target_pattern")

    assert result == []
```

### 3.3 差分の要点

- 新規ファイル。`list_files`/`read_file`/`search_code` それぞれについて、
  正常系・GCS_BUCKET 未設定・境界値（サイズ上限・件数上限）・異常系（不正な正規表現）を検証。
- `google.cloud.storage` は事前スタブでモック化し、実 GCS アクセスは発生しない。
- `_make_blob()` ヘルパーで `MagicMock` ベースの blob を組み立て、
  `list_blobs`/`bucket().blob()` いずれのアクセスパターンにも対応させている。

---

## 4. この編集単位の完了条件

- [ ] `pytest tests/test_a2a.py -q` が全緑。
- [ ] `pytest tests/test_tools.py -q` が全緑。
- [ ] `pytest -q`（プロジェクト全体）が全緑。
- [ ] `load_project_context_for_source` への参照が `tests/` 配下から完全に消えている
      （`grep -rn load_project_context tests/` がヒットしないこと）。

## 5. 依存

- [01-gcs-client.md](01-gcs-client.md)〜[04-a2a-router.md](04-a2a-router.md) — すべて完了していること。
  未完了のまま本ファイルのテストを実行すると、削除済み関数の import エラーや
  シグネチャ不一致で失敗する。
