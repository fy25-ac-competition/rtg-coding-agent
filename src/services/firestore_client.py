"""
Firestore からプロジェクトメタデータを取得する。

コレクション: coding_projects/{project_id}
  name: str
  description: str
  gcs_bucket: str
  gcs_prefix: str  （通常 "<project_id>/"）
  language: str
  framework: str
  created_at: Timestamp
"""
from dataclasses import dataclass, field
from google.cloud import firestore
from src.config import FIRESTORE_DATABASE, GOOGLE_CLOUD_PROJECT

_COLLECTION = "coding_projects"


@dataclass
class ProjectMetadata:
    project_id: str
    name: str = ""
    description: str = ""
    gcs_bucket: str = ""
    gcs_prefix: str = ""
    language: str = ""
    framework: str = ""


def _client() -> firestore.Client:
    kwargs: dict = {"database": FIRESTORE_DATABASE}
    if GOOGLE_CLOUD_PROJECT:
        kwargs["project"] = GOOGLE_CLOUD_PROJECT
    return firestore.Client(**kwargs)


def get_project(project_id: str) -> ProjectMetadata | None:
    """Firestore からプロジェクトメタデータを取得する。存在しない場合は None。"""
    doc = _client().collection(_COLLECTION).document(project_id).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    return ProjectMetadata(
        project_id=project_id,
        name=data.get("name", ""),
        description=data.get("description", ""),
        gcs_bucket=data.get("gcs_bucket", ""),
        gcs_prefix=data.get("gcs_prefix", f"{project_id}/"),
        language=data.get("language", ""),
        framework=data.get("framework", ""),
    )


def save_project(meta: ProjectMetadata) -> None:
    """プロジェクトメタデータを Firestore に保存（上書き）する。"""
    _client().collection(_COLLECTION).document(meta.project_id).set({
        "name": meta.name,
        "description": meta.description,
        "gcs_bucket": meta.gcs_bucket,
        "gcs_prefix": meta.gcs_prefix,
        "language": meta.language,
        "framework": meta.framework,
    })
