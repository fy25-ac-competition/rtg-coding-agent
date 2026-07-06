"""
ADK LlmAgent に登録する GCS 探索ツール（読み取り専用）。

ADK は「ToolContext 型の引数を持つ関数」を自動的に FunctionTool としてラップし、
LLM が関数呼び出し（Function Calling）で使えるようにする。関数の docstring と型ヒントが
そのままツールのスキーマ（名前・説明・パラメータ）として LLM に提示されるため、
LLM が用途を正しく判断できるよう docstring は具体的に書くこと。

対象の project_id は LLM 側に渡させず、ToolContext.state 経由でセッションから取得する。
これにより LLM が project_id を誤って生成・改変するリスク（ハルシネーション）を排除する。
project_id は src/agents/coding_agent.py の run_query() が create_session 時に
state へ設定する（詳細は 03-coding-agent.md 参照）。
"""
from google.adk.tools import ToolContext

from src.services import gcs_client

_NOT_SPECIFIED_MSG = "[情報] 対象アプリが指定されていないため探索できません。"


def _project_id(tool_context: ToolContext) -> str | None:
    """セッション状態から対象アプリの project_id を取り出す。未設定なら None。"""
    return tool_context.state.get("project_id")


def list_project_files(tool_context: ToolContext) -> list[str]:
    """対象アプリのファイル一覧（相対パス）を返す。まず全体像を把握するために使う。"""
    pid = _project_id(tool_context)
    if not pid:
        return [_NOT_SPECIFIED_MSG]
    return gcs_client.list_files(pid)


def read_project_file(path: str, tool_context: ToolContext) -> str:
    """
    指定した相対パスのファイル内容を返す。
    path には list_project_files が返す相対パスをそのまま指定すること。
    """
    pid = _project_id(tool_context)
    if not pid:
        return _NOT_SPECIFIED_MSG
    return gcs_client.read_file(pid, path)


def search_project_code(pattern: str, tool_context: ToolContext) -> list[str]:
    """
    正規表現 pattern で対象アプリのコードを横断検索し、
    マッチした行を "パス:行番号: 内容" 形式のリストで返す（最大100件）。
    ファイル名やキーワードの手がかりから関連箇所を素早く見つけたいときに使う。
    """
    pid = _project_id(tool_context)
    if not pid:
        return [_NOT_SPECIFIED_MSG]
    return gcs_client.search_code(pid, pattern)
