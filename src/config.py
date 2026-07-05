import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# GOOGLE_GENAI_USE_VERTEXAI=1 のとき ADK が自動で Vertex AI バックエンドを使用する
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")

GCS_BUCKET = os.getenv("GCS_BUCKET", "")
