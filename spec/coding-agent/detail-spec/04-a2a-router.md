# 編集単位 4: src/routers/a2a.py（改修）

**依存**: [03-coding-agent.md](03-coding-agent.md) 完了後（`run_query(question, project_id=...)` の
新シグネチャに追随するため）

---

## 1. 対象ファイル / 変更種別

- ファイル: `src/routers/a2a.py`
- 種別: 改修（一括プロンプト注入の削除、`target_source` からの project_id 解決、
  `run_query` 呼び出しの引数変更）

## 2. 現状（Before）

2026-07-06 時点の全文（61行）:

```python
"""
A2A JSON-RPC 2.0 エンドポイント。

RTG 本体の A2ACodingAgentClient が送信するリクエストを受け取り、
Vertex AI (Gemini) の回答を A2A レスポンス形式で返す。

リクエスト: POST /
  - method: "message/send"
  - params.message.parts[0].text: 質問テキスト（RTG 側テンプレートで組み立て済み）
  - params.message.metadata.target_source: 対象アプリ識別子（オプション、debug-20260705 §4）

レスポンス: result.artifacts[0].parts[0].text に回答テキストを格納
"""
import logging

from fastapi import APIRouter, HTTPException

from src.agents.coding_agent import run_query
from src.schemas.a2a import A2ARequest, A2AResponse
from src.services.gcs_client import load_project_context_for_source

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=A2AResponse)
async def a2a_endpoint(body: A2ARequest) -> A2AResponse:
    """RTG からの A2A JSON-RPC 2.0 リクエストを処理する。"""
    if body.method != "message/send":
        raise HTTPException(status_code=400, detail=f"未対応の method: {body.method}")

    parts = body.params.message.parts
    if not parts or not parts[0].text:
        raise HTTPException(status_code=400, detail="params.message.parts が空です")

    question = parts[0].text

    # metadata.target_source から対象アプリ識別子を取得（オプション）
    target_source: str | None = None
    if body.params.message.metadata:
        target_source = body.params.message.metadata.get("target_source")

    # GCS からコード文脈を取得して質問に付加する（demo: ソース対応）
    code_context = load_project_context_for_source(target_source)
    if code_context:
        question = (
            question
            + f"\n\n## 対象アプリ({target_source})のコード文脈\n\n"
            + code_context
        )
        logger.info("target_source=%s のコード文脈を付加しました", target_source)

    try:
        answer = await run_query(question)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("エージェント実行エラー: %s", exc)
        raise HTTPException(status_code=502, detail=f"エージェントエラー: {exc}") from exc

    return A2AResponse.from_text(answer)
```

乖離チェック済み（[00-overview.md §4](00-overview.md#4-乖離チェック結果実ソース-vs-本-spec2026-07-06-時点)）。

## 3. 変更後（After）：完全なファイル全文

```python
"""
A2A JSON-RPC 2.0 エンドポイント。

RTG 本体の A2ACodingAgentClient が送信するリクエストを受け取り、
Vertex AI (Gemini) の回答を A2A レスポンス形式で返す。

リクエスト: POST /
  - method: "message/send"
  - params.message.parts[0].text: 質問テキスト（RTG 側テンプレートで組み立て済み）
  - params.message.metadata.target_source: 対象アプリ識別子（オプション、debug-20260705 §4）

レスポンス: result.artifacts[0].parts[0].text に回答テキストを格納

target_source（demo:<name>）から project_id を解決し、run_query に渡す。
以前はここで GCS のコード文脈を一括取得して質問文へ連結していたが、
ADK LlmAgent 側の探索ツール（src/agents/tools.py）が project_id を使って
自律的に GCS を探索する方式へ移行したため、質問文への注入は行わない。
"""
import logging

from fastapi import APIRouter, HTTPException

from src.agents.coding_agent import run_query
from src.schemas.a2a import A2ARequest, A2AResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=A2AResponse)
async def a2a_endpoint(body: A2ARequest) -> A2AResponse:
    """RTG からの A2A JSON-RPC 2.0 リクエストを処理する。"""
    if body.method != "message/send":
        raise HTTPException(status_code=400, detail=f"未対応の method: {body.method}")

    parts = body.params.message.parts
    if not parts or not parts[0].text:
        raise HTTPException(status_code=400, detail="params.message.parts が空です")

    question = parts[0].text

    # metadata.target_source から対象アプリ識別子を取得（オプション）
    target_source: str | None = None
    if body.params.message.metadata:
        target_source = body.params.message.metadata.get("target_source")

    # target_source（demo:<name>）から project_id を解決する。
    # それ以外の形式（github: 等）・未指定の場合は project_id=None とし、
    # run_query 側のツールが「対象アプリが指定されていない」旨を返す。
    project_id: str | None = None
    if target_source and target_source.startswith("demo:"):
        project_id = target_source[len("demo:"):]
        logger.info("target_source=%s を project_id=%s に解決しました", target_source, project_id)

    try:
        answer = await run_query(question, project_id=project_id)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("エージェント実行エラー: %s", exc)
        raise HTTPException(status_code=502, detail=f"エージェントエラー: {exc}") from exc

    return A2AResponse.from_text(answer)
```

## 4. 差分の要点

- **import 削除**: `from src.services.gcs_client import load_project_context_for_source`
- **削除**: 一括コード文脈取得・質問文への連結ブロック（旧 43〜51 行、
  `code_context = load_project_context_for_source(target_source)` から
  `logger.info("target_source=%s のコード文脈を付加しました", target_source)` まで）。
- **追加**: `target_source` から `project_id` を解決するブロック（`demo:` prefix のみ対応、
  従来の `load_project_context_for_source` 内の判定ロジックと同一の条件を踏襲）。
- **変更**: `run_query(question)` → `run_query(question, project_id=project_id)`。
- **モジュール docstring**: 一括注入方式からツール探索方式への移行を明記するよう更新。

## 5. 理由・設計意図

- ルーターの責務を「リクエストのパースと project_id の解決」に限定し、
  GCS 探索そのものはツール層（[02-agent-tools.md](02-agent-tools.md)）と
  エージェント層（[03-coding-agent.md](03-coding-agent.md)）に委譲する。
  これにより `a2a.py` は GCS の実装詳細（`gcs_client`）を知らなくてよくなる
  （実際 import が消える）。
- `demo:` 以外（`github:` 等）・未指定のケースは、旧 `load_project_context_for_source` と
  同じく「対象なし」として扱う。挙動の後方互換性を保つため。

## 6. 注意点・エッジケース

- `logger` と `logging` の import は、`project_id` 解決のログ出力および
  既存の `logger.exception(...)` で引き続き使用するため**削除しない**。
- `target_source` が `"demo:"` そのもの（名前部分が空文字）の場合、
  `project_id = ""` となる。この場合 [03-coding-agent.md](03-coding-agent.md) の
  `run_query` は `state={"project_id": ""}` を設定し、
  [02-agent-tools.md](02-agent-tools.md) の `_project_id()` は空文字を返す。
  ツール側の `if not pid:` は空文字も False 判定するため「対象アプリが指定されていない」扱いになり、
  安全側に倒れる（従来の `load_project_context_for_source` でも
  `load_project_context("")` が呼ばれ実質空文字列を返す挙動だったため、後方互換）。

## 7. この編集単位の完了条件

- [ ] `load_project_context_for_source` の import が削除されている。
- [ ] 一括コード文脈の質問文連結処理が完全に削除されている。
- [ ] `target_source` が `demo:<name>` のとき `project_id == "<name>"` になる。
- [ ] `target_source` が `None`／`demo:` 以外のとき `project_id is None` になる。
- [ ] `run_query` が `project_id` キーワード引数付きで呼ばれている。

## 8. 依存

- [03-coding-agent.md](03-coding-agent.md) — `run_query(question, project_id=None)` の
  新シグネチャが実装済みであることが前提。
