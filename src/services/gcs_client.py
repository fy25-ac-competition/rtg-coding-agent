"""
Google Cloud Storage からソースコードを読み込む。

バケット構造:
  gs://<GCS_BUCKET>/<project_id>/<ファイルパス>
"""
from google.cloud import storage
from src.config import GCS_BUCKET

_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".whl", ".pyc", ".pyo",
    ".map", ".lock",
}
_MAX_FILE_BYTES = 50_000     # 1 ファイルあたり最大 50 KB
_MAX_TOTAL_BYTES = 300_000   # コード文脈全体の最大 300 KB


def load_project_context(project_id: str) -> str:
    """
    GCS の <project_id>/ プレフィックス以下のファイルを読み込み、
    LLM に渡すコード文脈文字列を組み立てて返す。
    """
    if not GCS_BUCKET:
        return ""

    client = storage.Client()
    prefix = f"{project_id}/"
    blobs = sorted(client.list_blobs(GCS_BUCKET, prefix=prefix), key=lambda b: b.name)

    parts: list[str] = []
    total = 0

    for blob in blobs:
        relative_path = blob.name[len(prefix):]
        if not relative_path:
            continue

        suffix = "." + relative_path.rsplit(".", 1)[-1].lower() if "." in relative_path else ""
        if suffix in _SKIP_EXTENSIONS:
            continue
        if blob.size > _MAX_FILE_BYTES or total + blob.size > _MAX_TOTAL_BYTES:
            continue

        try:
            content = blob.download_as_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        parts.append(f"### {relative_path}\n```\n{content}\n```")
        total += blob.size

    return "\n\n".join(parts)


def upload_file(project_id: str, file_path: str, content: str) -> str:
    """ソースファイルを GCS にアップロードし、GCS URI を返す。"""
    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(f"{project_id}/{file_path}")
    blob.upload_from_string(content, content_type="text/plain")
    return f"gs://{GCS_BUCKET}/{project_id}/{file_path}"
