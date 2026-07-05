"""
Google Cloud Storage からソースコードを読み込む。

バケット構造:
  gs://<GCS_BUCKET>/<project_id>/<ファイルパス>

対象アプリ識別子（demo:<name>）から自動的に project_id を解決する:
  demo:system-m  →  gs://<GCS_BUCKET>/system-m/...
  demo:system-s  →  gs://<GCS_BUCKET>/system-s/...
"""
import logging

from google.cloud import storage
from src.config import GCS_BUCKET

logger = logging.getLogger(__name__)

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


def load_project_context_for_source(source: str | None) -> str:
    """
    target_source 識別子から GCS のコード文脈を読み込む。

    対応形式:
      demo:<name>   →  gs://<GCS_BUCKET>/<name>/ 以下を読み込む
      github:<url>  →  GCS への事前アップロードが必要なため現状はスキップ
      その他 / None →  空文字を返す
    """
    if not source or not GCS_BUCKET:
        return ""

    if source.startswith("demo:"):
        project_id = source[len("demo:"):]
    else:
        return ""

    try:
        context = load_project_context(project_id)
        if context:
            logger.debug("GCS から %s のコード文脈を取得しました", source)
        return context
    except Exception as exc:
        logger.warning("GCS からのコード文脈取得に失敗しました (source=%s): %s", source, exc)
        return ""
