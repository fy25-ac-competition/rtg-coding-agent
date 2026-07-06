# テスト実行レポート: test_buggy_service（スキルなし）

## 1. メタデータ
- **実行日時**: 2026-06-22 00:10:20
- **対象スクリプト**: `.claude/skills/auto-pytest-reporter/evals/workspace/fixtures/test_buggy_service.py`
- **テスト指示書**: `target_buggy_service.py の discount() と apply_tax() 関数が仕様通りに動作することを確認するテスト。`
- **最終ステータス**: FAILED
- **リトライ回数**: 0 / 5 回

## 2. テストの目的
価格計算ロジックの動作確認。

## 3. 実行結果サマリー
2 件 FAIL。アプリ側にバグ。

```
2 failed, 1 passed in 0.05s
  test_discount_10_percent: 1100.0 != 900.0
  test_apply_tax_10_percent: 900.0 != 1100.0
```

## 4. AI 原因分析
`target_buggy_service.py` の演算子符号が逆転。`discount` は `(1+rate)` → `(1-rate)` に、`apply_tax` は `(1-tax_rate)` → `(1+tax_rate)` に修正が必要。

## 6. アクションアイテム
`target_buggy_service.py` の修正が必要。Issue ドラフトは省略（スキルなし条件）。
