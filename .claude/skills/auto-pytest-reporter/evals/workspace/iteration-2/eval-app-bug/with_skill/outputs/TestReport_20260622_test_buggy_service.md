# テスト実行レポート: test_buggy_service

## 1. メタデータ
- **実行日時**: 2026-06-22 00:10:20
- **対象スクリプト**: `.claude/skills/auto-pytest-reporter/evals/workspace/fixtures/test_buggy_service.py`
- **テスト指示書**: `target_buggy_service.py の discount() と apply_tax() 関数が仕様通りに動作することを確認するテスト。1000円を10%引きにすると900円、1000円に消費税10%を加えると1100円になるべき。`
- **最終ステータス**: FAILED
- **リトライ回数**: 0 / 5 回（テストコードは正しいため修正せず）

## 2. テストの目的
価格計算ロジック（割引・税計算）が仕様通りに動作することを確認する。

## 3. 実行結果サマリー
テストコードは仕様通りに正しく記述されているが、`target_buggy_service.py` のアプリ実装に演算子符号の逆転バグがある。テストコードを修正しても PASS にならないため、アプリ側バグと判定。

```
test_discount_10_percent  FAILED  (期待: 900.0、実際: 1100.0)
test_discount_zero        PASSED
test_apply_tax_10_percent FAILED  (期待: 1100.0、実際: 900.0)
2 failed, 1 passed in 0.05s
```

## 4. 自己修復ログ（テストコード修正を試みなかった理由）
テストコードの `assert discount(1000.0, 0.1) == 900.0` は仕様（10%引き → 900円）として正しい。
アサーション値を変えることは仕様の改ざんになるため、テストコード修正を行わずアプリ側バグと判定した。

## 5. ログ参照
ログファイル: 省略

<details><summary>エラー抜粋（クリックして展開）</summary>

```text
FAILED test_buggy_service.py::test_discount_10_percent
  AssertionError: 期待値 900.0、実際 1100.0
  assert 1100.0 == 900.0

FAILED test_buggy_service.py::test_apply_tax_10_percent
  AssertionError: 期待値 1100.0、実際 900.0
  assert 900.0 == 1100.0
```

</details>

## 6. アクションアイテム
Issue #draft を起票済み（`issue_draft_20260622.md` を参照）。`target_buggy_service.py` のバグ修正が必要。
