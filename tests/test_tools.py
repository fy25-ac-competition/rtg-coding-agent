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

    # list_files は blob.name（"proj/" プレフィックス込みのフルパス）でソートするため、
    # ASCII 比較で大文字 "README.md" が小文字 "app.py" より前に来る。
    assert result == ["README.md", "app.py"]


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

    # パターン r"os\." は "os" の直後にドットが続く行のみマッチする。
    # "import os" はドットが続かないためマッチせず、3行目のみが該当する。
    assert result == ["app.py:3: return os.getcwd()"]


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
