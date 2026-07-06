"""
Google Cloud Storage 上のソースコードを探索するためのプリミティブ関数群。

バケット構造:
  gs://<GCS_BUCKET>/<project_id>/<ファイルパス>

以前はここでプロジェクト全体を一括ダンプして LLM プロンプトへ注入していたが、
ADK LlmAgent 側にツール（list_files / read_file / search_code をラップした
FunctionTool、src/agents/tools.py 参照）を持たせ、LLM が必要なファイルだけを
自律的に探索する方式へ移行した。一括ダンプ用の関数は本ファイルから削除済み。

対象アプリ識別子（demo:<name>）から自動的に project_id を解決する:
  demo:system-m  →  gs://<GCS_BUCKET>/system-m/...
  demo:system-s  →  gs://<GCS_BUCKET>/system-s/...
"""
import re

from google.cloud import storage
from src.config import GCS_BUCKET

_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".whl", ".pyc", ".pyo",
    ".map", ".lock",
}
_MAX_FILE_BYTES = 50_000       # 1 ファイルあたり最大 50 KB（read_file / search_code で適用）
_MAX_TOTAL_BYTES = 300_000     # 未使用（旧一括ダンプ用の定数だが後方互換のため残置）
_MAX_SEARCH_HITS = 100         # search_code が返すマッチ行の最大件数


def _skip_suffix(relative_path: str) -> bool:
    """スキップ対象拡張子（バイナリ・生成物）なら True。"""
    suffix = "." + relative_path.rsplit(".", 1)[-1].lower() if "." in relative_path else ""
    return suffix in _SKIP_EXTENSIONS


def list_files(project_id: str) -> list[str]:
    """
    <project_id>/ プレフィックス配下のファイル相対パス一覧を返す。
    スキップ拡張子（バイナリ・生成物）は除外する。GCS_BUCKET 未設定時は空リスト。
    """
    if not GCS_BUCKET:
        return []

    client = storage.Client()
    prefix = f"{project_id}/"
    result: list[str] = []
    for blob in sorted(client.list_blobs(GCS_BUCKET, prefix=prefix), key=lambda b: b.name):
        rel = blob.name[len(prefix):]
        if not rel or _skip_suffix(rel):
            continue
        result.append(rel)
    return result


def read_file(project_id: str, path: str) -> str:
    """
    <project_id>/<path> のファイル内容（UTF-8）を返す。
    存在しない/サイズ上限超/取得失敗時は、例外を投げず
    エラー内容を示す文字列を返す（LLM ツール応答として自然に扱えるようにするため）。
    """
    if not GCS_BUCKET:
        return "[エラー] GCS_BUCKET が未設定です。"

    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(f"{project_id}/{path}")
    if not blob.exists():
        return f"[エラー] ファイルが見つかりません: {path}"

    blob.reload()  # list_blobs 経由でないため size 等のメタデータを明示的に取得する
    if blob.size and blob.size > _MAX_FILE_BYTES:
        return f"[エラー] ファイルが大きすぎます（{blob.size} bytes > {_MAX_FILE_BYTES}）: {path}"

    try:
        return blob.download_as_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - 個別ファイルの取得失敗で全体を落とさない
        return f"[エラー] 読み込みに失敗しました: {path} ({exc})"


def search_code(project_id: str, pattern: str) -> list[str]:
    """
    <project_id>/ 配下のテキストファイルを正規表現 pattern で横断検索し、
    マッチ行を "<相対パス>:<行番号>: <行内容>" 形式で返す（最大 _MAX_SEARCH_HITS 件）。
    バイナリ・サイズ上限超のファイルはスキップする。pattern が不正な正規表現の場合は
    例外を投げずエラー文字列 1 件のリストを返す。
    """
    if not GCS_BUCKET:
        return ["[エラー] GCS_BUCKET が未設定です。"]
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return [f"[エラー] 正規表現が不正です: {exc}"]

    client = storage.Client()
    prefix = f"{project_id}/"
    hits: list[str] = []
    for blob in sorted(client.list_blobs(GCS_BUCKET, prefix=prefix), key=lambda b: b.name):
        rel = blob.name[len(prefix):]
        if not rel or _skip_suffix(rel):
            continue
        if blob.size and blob.size > _MAX_FILE_BYTES:
            continue
        try:
            text = blob.download_as_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - 個別ファイルの取得失敗はスキップして続行
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{rel}:{lineno}: {line.strip()}")
                if len(hits) >= _MAX_SEARCH_HITS:
                    return hits
    return hits
