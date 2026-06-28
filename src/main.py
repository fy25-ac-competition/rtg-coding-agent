from fastapi import FastAPI
from src.routers.generate import router as generate_router

app = FastAPI(
    title="RTG Coding Agent",
    description="GCS に保存されたソースコードを Vertex AI で分析し実装計画を生成するエージェント",
    version="0.5.0",
)

app.include_router(generate_router)
