from typing import Optional
from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    input_text: str = Field(description="ユーザーの変更要求（自然言語）")
    target_source: str = Field(default="", description="対象プロジェクト識別子（gcs:<project_id> 等）")
    target_context: str = Field(default="", description="コード文脈の直接指定（target_source より優先）")


class FileChange(BaseModel):
    path: str = Field(description="変更するファイルのパス")
    description: str = Field(description="変更内容の説明")
    content: Optional[str] = Field(default=None, description="変更後のファイル内容（全体）")
    diff: Optional[str] = Field(default=None, description="unified diff 形式（content と排他）")


class GenerationResult(BaseModel):
    explanation: str = Field(description="実装方針の説明")
    file_changes: list[FileChange] = Field(description="変更するファイル一覧")
    commands: list[str] = Field(description="実行するコマンド（順序通り）")
