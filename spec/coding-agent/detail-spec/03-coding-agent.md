# 編集単位 3: src/agents/coding_agent.py（改修）

**依存**: [02-agent-tools.md](02-agent-tools.md) 完了後（`tools=` に登録する3関数が必要なため）

---

## 1. 対象ファイル / 変更種別

- ファイル: `src/agents/coding_agent.py`
- 種別: 改修（`LlmAgent` へのツール登録、instruction 追記、`run_query` シグネチャ変更）

## 2. 現状（Before）

2026-07-06 時点の全文（69行）:

```python
"""
RTG コーディングエージェント (A2A 対応版)。

RTG 本体から受け取った質問テキストを Vertex AI (Gemini) に投げ、
テキスト回答を返す。output_schema は使用しない（プレーンテキスト応答が必要なため）。
回答は run_async イベントのテキストパーツを収集して組み立てる。
"""
import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.config import GEMINI_MODEL

_APP_NAME = "rtg-coding-agent"
_LOCAL_TIMEOUT = 60.0

_session_svc = InMemorySessionService()

_agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="RTG の指示に従い spec 作成・コマンド生成・影響調査等を行うコーディングエージェント",
    instruction=(
        "あなたはシニアソフトウェアエンジニアです。"
        "受け取った指示の種別に応じた回答をテキストのみで返してください。\n\n"
        "## 回答スタイル(指示種別ごと)\n"
        "- spec 作成・更新: Markdown 形式。"
        "## 実現方針 / ## 変更範囲 / ## 手順 の3セクション構成を推奨。\n"
        "- コマンドリスト生成: 1行1コマンド・コマンドのみ(説明・番号・コードフェンス不要)。\n"
        "- 影響調査: 影響範囲・関連コード名・変更箇所を含めた簡潔な日本語報告文。\n"
        "- 模擬実行結果: 実際のシステムには変更を加えない前提で結果を日本語で報告。\n"
        "- 拒否通知: 「了解しました。実行しません。」等の簡潔な確認文。\n"
        "- ユースケース候補: 「〜したい」形式で1行1件、2〜3件列挙。\n"
        "コードブロック(```)で全体を囲まないこと。"
    ),
)

_runner = Runner(agent=_agent, session_service=_session_svc, app_name=_APP_NAME)


async def run_query(question: str) -> str:
    """LLM に質問を投げてテキスト回答を返す。タイムアウト時は ValueError を送出。"""
    session = await _session_svc.create_session(app_name=_APP_NAME, user_id="system")
    message = types.Content(role="user", parts=[types.Part(text=question)])

    collected: list[str] = []

    try:
        async with asyncio.timeout(_LOCAL_TIMEOUT):
            async for event in _runner.run_async(
                user_id="system",
                session_id=session.id,
                new_message=message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            collected.append(part.text)
    except TimeoutError as exc:
        raise ValueError(f"エージェントがタイムアウトしました({_LOCAL_TIMEOUT}秒)") from exc

    if not collected:
        raise ValueError("エージェントからの応答が空でした")

    return "".join(collected)
```

乖離チェック済み（[00-overview.md §4](00-overview.md#4-乖離チェック結果実ソース-vs-本-spec2026-07-06-時点)）。

## 3. 変更後（After）：完全なファイル全文

```python
"""
RTG コーディングエージェント (A2A 対応版)。

RTG 本体から受け取った質問テキストを Vertex AI (Gemini) に投げ、
テキスト回答を返す。output_schema は使用しない（プレーンテキスト応答が必要なため）。
回答は run_async イベントのテキストパーツを収集して組み立てる。

GCS 上の対象アプリコードは一括プロンプト注入ではなく、LlmAgent に登録した
探索ツール（src/agents/tools.py）を通じて LLM が自律的に読みに行く方式を採る。
対象アプリの project_id はセッション状態 (state["project_id"]) 経由でツールに渡す。
"""
import asyncio

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.tools import (
    list_project_files,
    read_project_file,
    search_project_code,
)
from src.config import GEMINI_MODEL

_APP_NAME = "rtg-coding-agent"
_LOCAL_TIMEOUT = 120.0  # 複数回のツール呼び出し（探索→読み込み→回答）を許容するため 60→120 秒に変更

_session_svc = InMemorySessionService()

_agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="RTG の指示に従い spec 作成・コマンド生成・影響調査等を行うコーディングエージェント",
    instruction=(
        "あなたはシニアソフトウェアエンジニアです。"
        "受け取った指示の種別に応じた回答をテキストのみで返してください。\n\n"
        "## 探索方針\n"
        "対象アプリのコードに関わる指示(spec 作成・影響調査・ユースケース候補等)では、"
        "推測で回答せず、まず list_project_files で全体像を掴み、read_project_file / "
        "search_project_code で関連コードを確認してから回答すること。"
        "対象アプリが指定されていない(ツールが「指定されていない」旨を返す)場合は、"
        "ツールを使わず一般的な方針として回答すること。\n\n"
        "## 回答スタイル(指示種別ごと)\n"
        "- spec 作成・更新: Markdown 形式。"
        "## 実現方針 / ## 変更範囲 / ## 手順 の3セクション構成を推奨。\n"
        "- コマンドリスト生成: 1行1コマンド・コマンドのみ(説明・番号・コードフェンス不要)。\n"
        "- 影響調査: 影響範囲・関連コード名・変更箇所を含めた簡潔な日本語報告文。\n"
        "- 模擬実行結果: 実際のシステムには変更を加えない前提で結果を日本語で報告。\n"
        "- 拒否通知: 「了解しました。実行しません。」等の簡潔な確認文。\n"
        "- ユースケース候補: 「〜したい」形式で1行1件、2〜3件列挙。\n"
        "コードブロック(```)で全体を囲まないこと。"
    ),
    tools=[list_project_files, read_project_file, search_project_code],
)

_runner = Runner(agent=_agent, session_service=_session_svc, app_name=_APP_NAME)


async def run_query(question: str, project_id: str | None = None) -> str:
    """
    LLM に質問を投げてテキスト回答を返す。タイムアウト時は ValueError を送出。

    project_id を渡すと、セッション状態経由で探索ツール（list_project_files 等）が
    該当プロジェクトの GCS コードを参照できるようになる。None の場合、ツールは
    「対象アプリが指定されていない」旨を返し、LLM は一般論で回答する。
    """
    session = await _session_svc.create_session(
        app_name=_APP_NAME,
        user_id="system",
        state={"project_id": project_id},
    )
    message = types.Content(role="user", parts=[types.Part(text=question)])

    collected: list[str] = []

    try:
        async with asyncio.timeout(_LOCAL_TIMEOUT):
            async for event in _runner.run_async(
                user_id="system",
                session_id=session.id,
                new_message=message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            collected.append(part.text)
    except TimeoutError as exc:
        raise ValueError(f"エージェントがタイムアウトしました({_LOCAL_TIMEOUT}秒)") from exc

    if not collected:
        raise ValueError("エージェントからの応答が空でした")

    return "".join(collected)
```

## 4. 差分の要点

- **import 追加**: `from src.agents.tools import list_project_files, read_project_file, search_project_code`
- **`_LOCAL_TIMEOUT`**: `60.0` → `120.0`。
- **`_agent` に `tools=[list_project_files, read_project_file, search_project_code]` を追加**。
- **`instruction` の先頭**（既存の「あなたはシニアソフトウェアエンジニアです。」の直後、
  「## 回答スタイル」の直前）に **「## 探索方針」セクションを新規挿入**。既存の
  回答スタイル指示・末尾の「コードブロックで囲まない」指示はそのまま維持。
- **`run_query`**: シグネチャに `project_id: str | None = None` を追加。
  `create_session` 呼び出しに `state={"project_id": project_id}` を追加。
  ループ・タイムアウト処理・戻り値組み立ては変更なし。

## 5. 理由・設計意図

- タイムアウトを 120 秒に延ばすのは、探索ツールを使うフローでは
  `list_project_files` → `read_project_file`（複数回）→ 最終回答、という
  マルチターンの Function Calling が発生し、単発質問より応答時間が伸びるため。
- `create_session(..., state={"project_id": project_id})` は
  [02-agent-tools.md](02-agent-tools.md) の `_project_id(tool_context)` が
  `tool_context.state.get("project_id")` で読み取る値の設定元。
  `project_id=None` の場合も `state={"project_id": None}` として明示的に渡し、
  ツール側の `if not pid:` 判定で「未指定」扱いにする。

## 6. 注意点・エッジケース

- **ADK バージョン差異**: `InMemorySessionService.create_session()` が `state` キーワードを
  受け付けないバージョンでは、以下のように代替すること
  （[00-overview.md §3](00-overview.md#3-共通前提) 参照）:
  ```python
  session = await _session_svc.create_session(app_name=_APP_NAME, user_id="system")
  session.state["project_id"] = project_id
  ```
  実装時に `create_session` のシグネチャを確認し、`state` 引数が使えるかどうかで
  上記いずれかを選択すること。
- instruction 文字列は既存コードに合わせて ````` 部分をそのまま維持し、
  スタイルの一貫性（三点リーダーの使い方、句読点無し等）を崩さないこと。

## 7. この編集単位の完了条件

- [ ] `_agent` に `tools=` が設定され、3 関数が渡っている。
- [ ] instruction に「## 探索方針」セクションが追加され、既存の回答スタイル指示が保持されている。
- [ ] `run_query(question, project_id=None)` が動作し、`project_id` を渡した場合に
      セッション状態へ反映されることを確認できる（実際の ADK ランタイムまたは
      [05-tests.md](05-tests.md) のモックで検証）。
- [ ] `_LOCAL_TIMEOUT` が `120.0` になっている。

## 8. 依存

- [02-agent-tools.md](02-agent-tools.md) — `list_project_files`/`read_project_file`/
  `search_project_code` が実装済みであることが前提。
