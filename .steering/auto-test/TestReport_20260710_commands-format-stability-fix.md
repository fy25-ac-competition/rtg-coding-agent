# テスト実行レポート: commands-format-stability-fix

## 1. メタデータ
- **実行日時**: 2026-07-10
- **対象spec**: `spec/output-spec-or-commands/commands-format-stability-fix-spec.md`
- **対象スクリプト**: `tests/` 一式（pytest回帰）＋ A/B検証用一時スクリプト（`scratchpad/ab_verify_fix.py`、コミット対象外）
- **最終ステータス**: SUCCESS（総合判定 PASS）
- **リトライ回数**: 0 / 5 回（pytest側）

## 2. テストの目的
`src/agents/coding_agent.py` の `_INSTRUCTION` に、診断で確定した2つの失敗メカニズム
（notify_approval の実行権限を理由にした誤った拒否／generate_command_list の
ツール呼び出し疑似構文の混入）へ対応する4ブロックを追記した修正が、

1. 既存の静的検証（`test_instruction.py`）・A2Aルーター回帰（`test_a2a.py`）・
   GCS探索プリミティブ（`test_tools.py`）を壊していないこと
2. `generate_command_list`／`notify_approval` の commands 形式マッピング精度を
   実際に改善していること（実 Vertex AI 呼び出しによる定量確認）

を担保することが目的。

## 3. 実行結果サマリー

### 3.1 pytest回帰（工程2 / spec §6 Step1）

`./venv/bin/python -m pytest tests/ -v` — **26件全件 PASSED**（既存 `test_instruction.py`
5ケースを含む。今回の修正は既存文言を削除していないため、そのまま通過）。

### 3.2 A/B検証（工程3 / spec §6 Step2、実 Vertex AI 呼び出し）

`genki.watanuki@gmail.com`（project: `vertex-and-gemini-usage-test`, region: `us-central1`,
model: `gemini-2.5-flash`）を用い、`Runner.run_async` を直接呼び出すスクリプトで
`generate_command_list`・`notify_approval` を各 **N=8回** 実行し、6分類で判定した。

| パターン | commands-correct | tool-name-leak | spec-refusal | spec-other | empty | rate-limited | 合否 |
|---|---|---|---|---|---|---|---|
| generate_command_list | **8/8** | 0 | 0 | 0 | 0 | 0 | **PASS** |
| notify_approval | **8/8** | 0 | 0 | 0 | 0 | 0 | **PASS** |

**総合判定: PASS**（合格基準: 各パターンでN=8中6以上がcommands-correct、かつ
tool-name-leak・spec-refusalが0件 — 両パターンとも8/8で基準を大幅に上回り達成）。

修正前の初回診断（`commands-format-stability-fix-spec.md` §2 参照）では
generate_command_list が有効試行中約50%、notify_approval が50%の誤マッピング率
だったのに対し、修正後は両パターンとも**8/8（100%）が正しいcommands形式**となり、
かつ診断で確認された2つの不具合（ツール名混入・実行権限を理由にした拒否）は
**一度も再発しなかった**。

## 4. 自己修復ログ
リトライなし（pytest・A/Bとも初回で目標達成）。

## 5. ログ参照
- pytest実行ログ: 本レポート作成時にコンソールへ出力（26 passed, 1 warning, 0.31s）。
- A/B検証詳細ログ・全16試行の応答プレビュー: `scratchpad/ab_verify_fix_result.md`
  （セッション固有の一時ディレクトリ。リポジトリ外のため恒久保存はされない。
  必要な要点は本レポート §3.2 に転記済み）。

<details><summary>A/B検証の代表的な応答例（クリックして展開）</summary>

```text
[generate_command_list attempt 1]
touch coupon_service.py
vi cart.js
touch test_coupon_feature.py

[notify_approval attempt 4]
ALTER TABLE orders ADD COLUMN coupon_id INTEGER;
pytest tests/test_order_service.py -v
```

いずれもツール呼び出し構文（`list_project_files()` 等）や実行権限を理由にした
拒否文言は含まれず、素朴なコマンド列のみが返っている。

</details>

## 6. アクションアイテム
対応不要。`commands-format-stability-fix-spec.md` の完了条件をすべて満たした。

**参考**: 本修正は `spec/output-spec-or-commands/output-spec-or-commands-spec.md` および
`.steering/auto-test/TestReport_20260710_output-spec-or-commands.md`（2形式ポリシー本体の
検証記録）を上書きせず、追加修正として独立に記録している。
