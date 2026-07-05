"""
A2A JSON-RPC 2.0 リクエスト / レスポンス スキーマ。

RTG 本体（a2a_client.py）が送受信するワイヤ形式に完全準拠:
  - リクエスト: POST / へ jsonrpc 2.0 message/send
  - metadata.target_source: 対象アプリ識別子（debug-20260705 spec §4 の新フィールド）
  - レスポンス: result.artifacts[0].parts[0].text に回答テキストを格納
"""
from pydantic import BaseModel


class A2APart(BaseModel):
    text: str


class A2AMessage(BaseModel):
    role: str = "user"
    parts: list[A2APart]
    metadata: dict | None = None


class A2AParams(BaseModel):
    message: A2AMessage


class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int = 1
    method: str = "message/send"
    params: A2AParams


class A2AResponsePart(BaseModel):
    text: str


class A2AArtifact(BaseModel):
    parts: list[A2AResponsePart]


class A2AResult(BaseModel):
    artifacts: list[A2AArtifact]


class A2AResponse(BaseModel):
    result: A2AResult

    @classmethod
    def from_text(cls, text: str) -> "A2AResponse":
        """回答テキストから A2A レスポンスを組み立てる。"""
        return cls(result=A2AResult(artifacts=[A2AArtifact(parts=[A2AResponsePart(text=text)])]))
