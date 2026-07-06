# テスト実行レポート: adk-tools（ADK探索ツール導入）

## 1. メタデータ
- **実行日時**: 2026-07-06 20:51:38
- **対象スクリプト**: `tests/test_a2a.py`, `tests/test_tools.py`（プロジェクト全体 `pytest -q`）
- **テスト指示書**: ADK探索ツール導入（`spec/coding-agent/adk-tools-spec.md`）。GCS探索プリミティブ
  （list_files/read_file/search_code）と ADK ツールラッパー
  （list_project_files/read_project_file/search_project_code）、a2a ルーターの project_id 解決、
  coding_agent の tools 登録・run_query シグネチャ変更を実装。DoD は「pytest -q が全緑」。
- **最終ステータス**: SUCCESS
- **リトライ回数**: 1 / 5 回

## 2. テストの目的
一括プロンプト注入方式から ADK LlmAgent のツール探索方式への移行が正しく機能するかを検証する。
具体的には (1) GCS 探索プリミティブ 3 種のロジック（境界値・異常系含む）、
(2) A2A ルーターが `target_source` から `project_id` を正しく解決し `run_query` に渡すこと、
(3) 既存の A2A エンドポイントの振る舞い（正常系・異常系）が回帰していないこと。

## 3. 実行結果サマリー
初回実行は環境未整備（`fastapi`/`python-dotenv` 等未インストール）により collection error
（ENV_ERROR）。ユーザー確認の上で `.venv` を新規作成し `requirements.txt` + `pytest` をインストール後、
再実行したところ 2 件の AssertionError が発生。原因を精査した結果、いずれも実装ではなく
**テストの期待値記述ミス**（自己修復対象）と判断し `tests/test_tools.py` のみを修正。
再々実行で **21件全件 PASSED**。

## 4. 自己修復ログ
| 回数 | 修正ファイル | 修正内容の要約 | 結果 |
|------|------------|--------------|------|
| 1 | tests/test_tools.py | `test_list_files_excludes_skip_extensions`: `list_files` は blob.name（フルパス）で ASCII ソートするため、大文字 `README.md` が小文字 `app.py` より前に来る。期待値を `["README.md", "app.py"]` に修正。 | 再実行で解消 |
| 1 | tests/test_tools.py | `test_search_code_returns_matching_lines`: 正規表現 `r"os\."` は「os」の直後にドットが続く行のみマッチし、「import os」はマッチしない。期待値から不一致だった `"app.py:1: import os"` を削除。 | 再実行で解消 |

## 5. ログ参照
- ログファイル: `.steering/auto-test/log/test_20260706_205138_3.log`
  （直前の失敗ログ: `test_20260706_205030_2.log`、初回 ENV_ERROR ログ: `test_20260706_204820.log`）

<details><summary>ログ抜粋（クリックして展開）</summary>

```text
tests/test_a2a.py::test_a2a_spec_creation PASSED
tests/test_a2a.py::test_a2a_command_list PASSED
tests/test_a2a.py::test_a2a_with_target_source_metadata PASSED
tests/test_a2a.py::test_a2a_notify_rejection PASSED
tests/test_a2a.py::test_a2a_suggest_usecases PASSED
tests/test_a2a.py::test_a2a_no_target_source_means_no_project_id PASSED
tests/test_a2a.py::test_a2a_non_demo_target_source_means_no_project_id PASSED
tests/test_a2a.py::test_a2a_invalid_method PASSED
tests/test_a2a.py::test_a2a_empty_parts PASSED
tests/test_a2a.py::test_a2a_agent_timeout PASSED
tests/test_a2a.py::test_a2a_agent_unexpected_error PASSED
tests/test_tools.py::test_list_files_excludes_skip_extensions PASSED
tests/test_tools.py::test_list_files_empty_bucket_config_returns_empty PASSED
tests/test_tools.py::test_read_file_returns_content PASSED
tests/test_tools.py::test_read_file_not_found PASSED
tests/test_tools.py::test_read_file_too_large PASSED
tests/test_tools.py::test_read_file_bucket_unset PASSED
tests/test_tools.py::test_search_code_returns_matching_lines PASSED
tests/test_tools.py::test_search_code_invalid_regex_returns_error_entry PASSED
tests/test_tools.py::test_search_code_respects_max_hits PASSED
tests/test_tools.py::test_search_code_skips_oversized_files PASSED
======================== 21 passed, 1 warning in 0.49s ========================
```

</details>

## 6. アクションアイテム
対応不要。全 21 件 PASSED。新規作成した `.venv`（google-adk 等は未インストール。テストはモックで代替）は
今後のテスト実行にも再利用可能。
