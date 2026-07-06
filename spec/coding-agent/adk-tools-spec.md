# ADK 探索ツール導入 spec（概要）

**バージョン**: v1.1.0 / **作成日**: 2026-07-06 / **対象リポジトリ**: rtg-coding-agent

## 1. 目的

RTG Coding Agent の ADK `LlmAgent` に、GCS 上の対象アプリコードを**自律的に探索**するための
読み取り専用ツール 3 種（Claude Code の LS/Glob・Read・Grep 相当）を FunctionTool として追加する。
併せて、既存の「全ファイル一括プロンプト注入」方式を**廃止**し、ツール探索へ一本化する。

## 2. 背景（現状の課題）

- `src/agents/coding_agent.py` の `LlmAgent` には `tools=` が無く、LLM が自律探索できない。
- `src/routers/a2a.py` が `load_project_context_for_source()` で対象プロジェクトの全ファイルを
  一括ダンプしてプロンプトへ注入している。
- コード文脈全体 300KB 上限（`gcs_client.py` の `_MAX_TOTAL_BYTES`）を超えると単純に切り捨てられ、
  大規模プロジェクトで破綻。無関係ファイルまで毎回載りトークンを浪費。

## 3. スコープ

### やること
- GCS プリミティブ 3 種を `gcs_client.py` に追加（list / read / search）。
- ADK ツールラッパー `src/agents/tools.py` を新規作成（`ToolContext.state` から project_id 取得）。
- `coding_agent.py` の `LlmAgent` に `tools=` 登録、instruction に探索手順を追記、
  `run_query` に `project_id` を追加、タイムアウトを 60→120 秒へ。
- `a2a.py` から一括注入を削除し、`target_source` → project_id 解決のみ残す。
- 一括注入用関数 `load_project_context` / `load_project_context_for_source` を削除。
- テスト更新（`tests/test_a2a.py`）と新規テスト（`tests/test_tools.py`）。

### やらないこと（対象外）
- 書き込み・編集・コマンド実行系ツール（Write/Edit/Bash 相当）。本エージェントは実装計画と
  コマンドを**テキストで返す**役割であり、実際の変更・実行は RTG 側の責務のため。
- `github:<url>` 形式ソースの取得（従来どおり非対応。GCS 事前アップロード前提）。

## 4. 追加ツール一覧

| ツール関数 | Claude Code 相当 | 役割 |
|---|---|---|
| `list_project_files` | LS / Glob | 対象アプリのファイル一覧（相対パス）を返す |
| `read_project_file(path)` | Read | 指定パスのファイル内容を返す |
| `search_project_code(pattern)` | Grep | 正規表現でコード横断検索し、マッチ行を返す |

対象 project_id は LLM に渡させず、セッション状態（`ToolContext.state["project_id"]`）から取得する。

## 5. 影響ファイル

| ファイル | 変更種別 |
|---|---|
| `src/services/gcs_client.py` | 改修（プリミティブ追加・一括ロード削除） |
| `src/agents/tools.py` | 新規 |
| `src/agents/coding_agent.py` | 改修 |
| `src/routers/a2a.py` | 改修 |
| `tests/test_a2a.py` | 改修 |
| `tests/test_tools.py` | 新規 |

## 6. 完了条件

- `pytest -q` が全緑。
- `metadata.target_source="demo:<name>"` を含む `message/send` リクエストで、ADK ログ上
  `list_project_files` → `read_project_file`/`search_project_code` が呼ばれ回答が返る。
- 300KB 超のプロジェクトでも切り捨てなく回答できる。

詳細な実装コード・編集差分・テスト仕様は `detail-spec/00-overview.md` を起点に、
`detail-spec/01-gcs-client.md`〜`05-tests.md` を参照（編集単位ごとに 1 ファイルへ分割済み）。

## 7. Claude Code での実装手順

別セッションの Claude Code がこの spec を渡されて実装に着手する際は、以下の手順で進めること。

1. **概観の把握**: `detail-spec/00-overview.md` を読み、編集単位一覧・依存順序（後述）・
   共通前提（ADK バージョン差異への備え等）を把握する。
2. **編集単位ごとに順番に実装**: 依存関係があるため、必ず以下の順序で 1 ファイル＝1 編集単位として進める。
   逆順・並行編集は import エラーやテスト不整合の原因になるため避けること。
   1. `detail-spec/01-gcs-client.md` → `src/services/gcs_client.py`
   2. `detail-spec/02-agent-tools.md` → `src/agents/tools.py`（新規）
   3. `detail-spec/03-coding-agent.md` → `src/agents/coding_agent.py`
   4. `detail-spec/04-a2a-router.md` → `src/routers/a2a.py`
   5. `detail-spec/05-tests.md` → `tests/test_a2a.py` 改修 + `tests/test_tools.py`（新規）
3. **各編集単位内の確認**: 各 detail-spec 末尾の「この編集単位の完了条件」チェックリストを、
   実装直後にその場で満たしていることを確認してから次の単位に進む。
4. **着手前の再確認（乖離チェック）**: 各 detail-spec の「現状（Before）」節は
   2026-07-06 時点のソースを基に記述している。実装着手時点で該当ファイルを一度 Read し、
   Before 節の記載と実際のソースに食い違いがないか確認すること
   （計画立案後に別セッションが手を入れている可能性があるため）。差異があれば、
   その差異を踏まえて After 節の変更を適用し直す。
5. **意味のある単位でコミット**: 各編集単位が完了するごとに、意味的なまとまりでコミットしてよい
   （例: `feat: gcs探索プリミティブ追加`, `feat: ADK探索ツールを新設`,
   `feat: coding_agentにtools登録`, `refactor: a2aルーターの一括注入を廃止`,
   `test: 探索ツール導入に伴うテスト更新`）。ユーザーからコミットの明示指示がない場合は
   作業ツリーへの変更のみに留め、コミットするかはユーザーに確認する。
6. **全体テスト**: 5 単位すべて完了後、`pytest -q` を実行し全緑になることを確認する。
7. **疎通確認**: `uvicorn src.main:app --port 8001` を起動し、
   `metadata.target_source="demo:<name>"` を含む `message/send` リクエストを送信、
   ADK ログ上で `list_project_files` → `read_project_file`/`search_project_code` の呼び出しと
   最終回答を確認する（GCS 上に該当 `demo:<name>` プロジェクトのファイルが必要）。
8. **spec との乖離を報告**: 実装内容が spec の記述と異なる判断をした箇所（ADK バージョン差異の
   代替コードを採用した等）があれば、作業報告時に明示する。
