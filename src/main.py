from fastapi import FastAPI
from src.routers.a2a import router as a2a_router

app = FastAPI(
    title="RTG Coding Agent",
    description="逆チューリングゲートからの A2A JSON-RPC 2.0 リクエストを処理し、Vertex AI で回答を生成するコーディングエージェント",
    version="1.0.0",
)

app.include_router(a2a_router)
