# detail-spec 概観・依存関係・乖離チェック結果

**バージョン**: v1.1.0 / **作成日**: 2026-07-06 / **対象リポジトリ**: rtg-coding-agent
**上位ドキュメント**: `../adk-tools-spec.md`（概要 spec）

このフォルダ (`spec/coding-agent/detail-spec/`) は、概要 spec で示した
「ADK LlmAgent に GCS 探索ツール 3 種（読み取り専用）を追加し、既存の一括プロンプト注入方式を
廃止する」実装を、**編集単位（＝改修/新規するソースファイル単位）ごと**に 1 ファイル 1 単位で
記述したものである。旧 `adk-tools-detail-spec.md`（単一ファイル版）はこのフォルダへ分割の上で廃止した。

---

## 1. 編集単位一覧

| # | 対象ファイル | 変更種別 | detail-spec |
|---|---|---|---|
| 1 | `src/services/gcs_client.py` | 改修（プリミティブ3種追加・一括ロード2関数削除） | [01-gcs-client.md](01-gcs-client.md) |
| 2 | `src/agents/tools.py` | 新規（ADK ツールラッパー） | [02-agent-tools.md](02-agent-tools.md) |
| 3 | `src/agents/coding_agent.py` | 改修（tools 登録・instruction・run_query） | [03-coding-agent.md](03-coding-agent.md) |
| 4 | `src/routers/a2a.py` | 改修（一括注入削除・project_id 解決） | [04-a2a-router.md](04-a2a-router.md) |
| 5 | `tests/test_a2a.py` 改修 + `tests/test_tools.py` 新規 | 改修＋新規 | [05-tests.md](05-tests.md) |

## 2. 推奨実装順序と依存関係

```
01-gcs-client (依存なし)
   └─▶ 02-agent-tools (01 の list_files/read_file/search_code を呼ぶ)
          └─▶ 03-coding-agent (02 の3関数を tools= に登録)
                 └─▶ 04-a2a-router (03 の run_query(project_id=...) シグネチャに追随)
                        └─▶ 05-tests (01〜04 すべての変更後の挙動を検証)
```

各 detail-spec は「上流が未完了だと動作確認できない」関係にあるため、**この順序を厳守**すること。
逆順・並行編集は import エラーやテスト失敗の原因になる。

## 3. 共通前提

- Python 依存は `requirements.txt` に記載済み。追加インストール不要。
  - `google-adk>=1.0.0`（`ToolContext` / FunctionTool 自動ラップ対応）
  - `google-cloud-storage>=2.19.0`
- 設定は `src/config.py`（`GEMINI_MODEL`, `GCS_BUCKET`, `GOOGLE_CLOUD_PROJECT`）。**変更不要**。
- GCS バケット構造: `gs://<GCS_BUCKET>/<project_id>/<ファイルパス>`。
- `target_source` 形式: `demo:<name>` → project_id は `<name>`。
  `github:<url>` および未指定は探索対象外（project_id=None）— 従来から非対応のため後方互換。
- **ADK API 差異への備え**（実装時に必ず現物の `google-adk` バージョンで検証すること）:
  - `ToolContext` の import は `from google.adk.tools import ToolContext` を第一候補とし、
    `ImportError` の場合は `from google.adk.tools.tool_context import ToolContext` を試す。
  - `InMemorySessionService.create_session(..., state=...)` がキーワード非対応の場合、
    `session = await create_session(...)` の後に `session.state["project_id"] = project_id` で代替する。

## 4. 乖離チェック結果（実ソース vs 本 spec、2026-07-06 時点）

計画立案時に `src/agents/coding_agent.py` / `src/routers/a2a.py` / `src/services/gcs_client.py` を
最新状態で読み直し、本 spec の記述と突き合わせた。結果は以下の通りで、**乖離は検出されなかった**。

| spec が前提とする記述 | 実ソースの該当箇所 | 判定 |
|---|---|---|
| `LlmAgent` に `tools=` 引数が存在しない | `coding_agent.py:22-39` | ✅ 一致 |
| `_LOCAL_TIMEOUT = 60.0` | `coding_agent.py:18` | ✅ 一致 |
| `run_query(question)` は単一引数、`create_session(app_name, user_id)` に `state` なし | `coding_agent.py:44-46` | ✅ 一致 |
| `a2a.py` が `load_project_context_for_source` を import し質問文へ一括連結 | `a2a.py:20`, `a2a.py:43-51` | ✅ 一致 |
| `gcs_client.py` に `load_project_context` / `load_project_context_for_source` が存在 | `gcs_client.py:27`, `gcs_client.py:64` | ✅ 一致 |
| `_MAX_FILE_BYTES=50_000` / `_MAX_TOTAL_BYTES=300_000` / `_SKIP_EXTENSIONS` の内容 | `gcs_client.py:18-24` | ✅ 一致 |
| `tests/test_a2a.py` の事前スタブ (12-17行) と各テストの `load_project_context_for_source` パッチ | `test_a2a.py:12-17`, `45`, `60`, `78`, `104`, `119`, `162`, `171` | ✅ 一致 |

このため各 detail-spec の「現状（Before）」節に記載したコード引用は、そのまま実装開始時の
差分ベースとして使用してよい。**ただし別セッションで実装に着手する時点では、必ず該当ファイルを
再度 Read し、この一覧と食い違いがないか（＝計画立案後に別の変更が加えられていないか）を
一度だけ確認すること。**

## 5. 完了条件（全体）

- 01〜05 すべての detail-spec 内チェックリストを満たす。
- `pytest -q` が全緑。
- `uvicorn src.main:app --port 8001` 起動後、`metadata.target_source="demo:<name>"` を含む
  `message/send` リクエストで ADK ログ上 `list_project_files` → `read_project_file`/
  `search_project_code` の呼び出しが確認でき、回答が返る。
- 300KB 超のプロジェクトでも（旧方式のような）切り捨てなく回答できる。
