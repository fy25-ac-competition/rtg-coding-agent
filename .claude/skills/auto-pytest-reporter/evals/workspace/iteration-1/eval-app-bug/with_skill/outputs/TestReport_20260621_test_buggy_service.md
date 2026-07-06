# テスト実行レポート: test_buggy_service（アプリ側バグ検出）

## 1. メタデータ
- **実行日時**: 2026-06-21 (eval iteration-1)
- **対象スクリプト**: `.claude/skills/open-github-issue-workspace/fixtures/test_buggy_service.py`
- **テスト指示書**: 「target_buggy_service.py の discount() と apply_tax() 関数が仕様通りに動作することを確認するテスト。1000円を10%引きにすると900円、1000円に消費税10%を加えると1100円になるべき。」
- **最終ステータス**: **FAILED**
- **リトライ回数**: 0 / 5（テストコードは正しいため、テスト側の修正は試みなかった）

## 2. テストの目的
`target_buggy_service.py` の `discount()`・`apply_tax()` が価格計算仕様（割引・税込）を正しく実装していることを確認する。

## 3. 実行結果サマリー
3テスト中 2 件が失敗。テストコードは仕様通りに正しく記述されており、失敗原因はアプリ側（`target_buggy_service.py`）の実装バグと判定。
`discount()` と `apply_tax()` で符号が逆転しており、割引が値上がり・税込みが税引きになっている。

**`target_buggy_service.py`（アプリ本体）は修正していない。**

## 4. 自己修復ログ
テストコードは仕様と整合しているため、修正は試みなかった。アプリ側バグとして即時 Issue 化対象と判定。

## 5. ログ参照

<details><summary>ログ抜粋（クリックして展開）</summary>

```text
============================= test session starts =============================
collecting ... collected 3 items

test_buggy_service.py::test_discount_10_percent FAILED [ 33%]
test_buggy_service.py::test_discount_zero PASSED [ 66%]
test_buggy_service.py::test_apply_tax_10_percent FAILED [100%]

================================== FAILURES ===================================
test_discount_10_percent:
  AssertionError: 期待値 900.0、実際 1100.0
  assert 1100.0 == 900.0

test_apply_tax_10_percent:
  AssertionError: 期待値 1100.0、実際 900.0
  assert 900.0 == 1100.0

2 failed, 1 passed in 0.08s
```

</details>

## 6. アクションアイテム
Issue ドラフトを生成済み: `issue_draft_20260621.md`

**Issue タイトル（案）**:
```
[Auto-Bug] target_buggy_service: discount/apply_tax の符号バグで価格計算が逆転
```

→ ユーザー確認後、`gh issue create` で起票する（[ISSUE_RULES.md](.github/ISSUE_RULES.md) 参照）。
