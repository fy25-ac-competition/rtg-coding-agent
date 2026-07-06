# 編集単位 2: src/agents/tools.py（新規作成）

**依存**: [01-gcs-client.md](01-gcs-client.md) 完了後（`gcs_client.list_files`/`read_file`/`search_code` を呼ぶため）

---

## 1. 対象ファイル / 変更種別

- ファイル: `src/agents/tools.py`（新規）
- 種別: 新規作成。ADK LlmAgent に登録する FunctionTool 用の薄いラッパー層。

## 2. 現状（Before）

存在しない（新規ファイル）。参考として、01 で改修済みの `src/services/gcs_client.py` の
公開関数シグネチャのみ再掲する（本ファイルが呼び出す対象）:

```python
def list_files(project_id: str) -> list[str]: ...
def read_file(project_id: str, path: str) -> str: ...
def search_code(project_id: str, pattern: str) -> list[str]: ...
```

## 3. 変更後（After）：完全なファイル全文

```python
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
```

## 4. 差分の要点

- 新規ファイル。公開関数は 3 つ: `list_project_files` / `read_project_file` / `search_project_code`。
- いずれも `tool_context: ToolContext` を最終引数（`read_project_file`/`search_project_code` では
  `path`/`pattern` の後）に取り、ADK にツールとして認識させる。
- 内部ヘルパー `_project_id()` で `tool_context.state.get("project_id")` を読み、
  未設定時は共通メッセージ `_NOT_SPECIFIED_MSG` を返す（3関数で表現を統一）。
- `gcs_client` の対応する関数へそのまま委譲するだけの薄いラッパー。

## 5. 理由・設計意図

- **project_id を関数引数として LLM に渡させない**設計にしたのは、複数プロジェクトが
  GCS 上に存在する場合に LLM が誤った project_id を生成・混同するリスクを避けるため。
  リクエストごとに一意に定まる対象（`target_source`）はサーバー側（ルーター）で解決し、
  セッション状態経由でツールに注入する（[03-coding-agent.md](03-coding-agent.md) の
  `run_query(question, project_id=...)` → `create_session(state={"project_id": project_id})`、
  [04-a2a-router.md](04-a2a-router.md) の `target_source` 解決を参照）。
- ツール関数の docstring が ADK のツールスキーマ（LLM に見える「関数の説明」）に
  直結するため、「まず全体像を把握するために使う」（list）「相対パスを指定すること」（read）
  「素早く見つけたいときに使う」（search）のように、**使い分けの手がかり**を明示した。
  これは `src/agents/coding_agent.py` の instruction に書く探索方針
  （[03-coding-agent.md §3.3](03-coding-agent.md)）と対になる設計。

## 6. 注意点・エッジケース

- **ADK バージョン差異**: `from google.adk.tools import ToolContext` で `ImportError` が出る場合、
  `from google.adk.tools.tool_context import ToolContext` に切り替える
  （[00-overview.md §3](00-overview.md#3-共通前提) 参照）。どちらが正しいかは実装時に
  `python -c "from google.adk.tools import ToolContext"` で確認すること。
- `tool_context.state` は dict ライクなオブジェクト。`.get("project_id")` で
  キー不在時も `None` を安全に返せる（`KeyError` にならない）。
- 3 関数とも戻り値は文字列またはリストであり、例外を送出しない
  （下層の `gcs_client` 側でエラーを文字列化しているため、ここでも踏襲）。

## 7. この編集単位の完了条件

- [ ] `src/agents/tools.py` が新規作成され、上記 3 関数と `_project_id`/`_NOT_SPECIFIED_MSG` を含む。
- [ ] `python -c "from src.agents.tools import list_project_files, read_project_file, search_project_code"`
      が例外なく通る（`google-adk` が未インストールの検証環境では
      [05-tests.md](05-tests.md) のスタブ方式を用いること）。
- [ ] 3 関数それぞれが `tool_context.state` に `project_id` が無い場合に
      `_NOT_SPECIFIED_MSG` を返すことを確認できる（単体テストは 05 でカバー）。

## 8. 依存

- [01-gcs-client.md](01-gcs-client.md) — `gcs_client.list_files`/`read_file`/`search_code` が
  実装済みであることが前提。
