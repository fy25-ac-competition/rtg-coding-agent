# テスト実行レポート: inout-casebook (test_inout_cases)

## 1. メタデータ
- **実行日時**: 2026-07-10 23:17:32
- **対象スクリプト**: `tests/test_inout_cases.py -m e2e`
- **テスト指示書**: `spec/output-spec-or-commands/inout-casebook-verification-spec.md`（In/Out 事例集検証 spec。`_INSTRUCTION` の2形式強制ポリシーに対し、代表10プロンプトの実出力を characterization としてカタログ化する）
- **最終ステータス**: SUCCESS
- **リトライ回数**: 0 / 5 回

## 2. テストの目的

`rtg-coding-agent` の `src/agents/coding_agent.py` の `_INSTRUCTION` は、RTG からの質問テキストの種別によらず応答を必ず「spec 形式」（`## 実現方針`/`## 変更範囲`/`## 手順` の3見出し構成）または「commands 形式」（1行1コマンドの生テキスト）のいずれかに強制する。本テストは、RTG の7メソッドから代表10プロンプト（`create_spec`×2, `edit_spec`×2, `generate_command_list`×2, `investigate_impact`×1, `notify_approval`×1, `notify_rejection`×1, `suggest_usecases`×1）を実 Vertex AI（Gemini）経由で `run_query()` に投げ、実出力を分類・記録する。

- **主基準（hard assert）**: 出力が `spec` または `commands` のいずれかに分類されること（`other` が0件）＝2形式不変条件。
- **従基準（observational・非hard assert）**: 期待形式（spec全文/コマンド列のどちらを想定していたか）と実際の分類が一致するかを記録するのみで、不一致でも失敗にしない。
- バグ探しではなく、現状実装（変更しない）に対する実出力の記録＝characterization が目的。

## 3. 実行結果サマリー

`./venv/bin/python -m pytest tests/test_inout_cases.py -m e2e -v` を1回実行し、**9 passed, 1 skipped**（リトライ・自己修復は不要、1発成功）。

- 2形式不変条件（5.1）は実行された9ケース全てで成立。`other` 判定は0件。
- `notify_approval-1` のみ `pytest.skip` された。テストハーネス内のレート制限判定ロジック（`tests/test_inout_cases.py` 内、`"RESOURCE_EXHAUSTED" in message or "429" in message` で `pytest.skip(...)`）により、Vertex AI 側のレート制限（429/RESOURCE_EXHAUSTED）が環境要因として自動的に skip 扱いとなったもの。spec 5.3 の定義どおりアプリ側バグとは判定しない。
- 期待形式と実出力分類の不一致（5.2, observational）: **0件**。記録された9ケース全てで `一致: True`（期待どおりの形式で出力された）。
- `git diff --stat` で `src/`・`schemas`・`routers` 配下に差分なしを確認済み（実装は一切変更していない）。

## 4. 自己修復ログ（リトライがあった場合）

リトライなし（1回目の実行で EXIT_CODE=0、全ケースが hard assert を満たした）。

## 5. ログ参照

- ログファイル: `.steering/output-spec-or-commands/log/test_20260710_231732.log`

<details><summary>ログ抜粋（クリックして展開）</summary>

```text
collecting ... collected 10 items

tests/test_inout_cases.py::test_inout_case[create_spec-1] PASSED         [ 10%]
tests/test_inout_cases.py::test_inout_case[create_spec-2] PASSED         [ 20%]
tests/test_inout_cases.py::test_inout_case[edit_spec-1] PASSED           [ 30%]
tests/test_inout_cases.py::test_inout_case[edit_spec-2] PASSED           [ 40%]
tests/test_inout_cases.py::test_inout_case[generate_command_list-1] PASSED [ 50%]
tests/test_inout_cases.py::test_inout_case[generate_command_list-2] PASSED [ 60%]
tests/test_inout_cases.py::test_inout_case[investigate_impact-1] PASSED  [ 70%]
tests/test_inout_cases.py::test_inout_case[notify_approval-1] SKIPPED    [ 80%]
tests/test_inout_cases.py::test_inout_case[notify_rejection-1] PASSED    [ 90%]
tests/test_inout_cases.py::test_inout_case[suggest_usecases-1] PASSED    [100%]

============ 9 passed, 1 skipped, 113 warnings in 197.26s (0:03:17) ============
```

</details>

## 6. アクションアイテム

対応不要。2形式不変条件は全実行ケースで成立しており、アプリ側バグは検出されなかった（Issue 化なし）。`notify_approval-1` は環境要因（Vertex AI レート制限）による skip のため、再実行して In/Out 事例集を10件に揃えたい場合は時間をおいて `tests/test_inout_cases.py -m e2e -k notify_approval-1` を再実行することを推奨する（本レポート時点では9/10ケースの記録に留まる）。

## 7. 追記（フォローアップ再実行）

本レポート作成の直後、レート制限解消を待って `notify_approval-1` のみ単独再実行した。

```
./venv/bin/python -m pytest "tests/test_inout_cases.py::test_inout_case[notify_approval-1]" -v -rs
======================== 1 passed, 15 warnings in 2.97s ========================
```

2形式不変条件が成立（`commands` 分類、期待形式と一致）。これにより **10/10 ケース全件が記録済み**となった
（`.steering/output-spec-or-commands/cases/` に10ファイル）。総合ステータス: **SUCCESS（10/10）**。
