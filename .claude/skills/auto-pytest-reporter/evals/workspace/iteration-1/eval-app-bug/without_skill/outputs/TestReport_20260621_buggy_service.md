# テスト実行レポート: buggy_service（スキルなし）

## 実行日時
2026-06-21 (eval iteration-1 baseline)

## テスト対象ファイル
`.claude/skills/open-github-issue-workspace/fixtures/test_buggy_service.py`

## 成功/失敗ステータス
**FAILED** — 2 failed, 1 passed

## ログ抜粋
```
FAILED test_buggy_service.py::test_discount_10_percent
  AssertionError: 期待値 900.0、実際 1100.0

FAILED test_buggy_service.py::test_apply_tax_10_percent
  AssertionError: 期待値 1100.0、実際 900.0

2 failed, 1 passed
```

## 失敗原因の分析
target_buggy_service.py の discount() と apply_tax() に符号バグがある。
discount() は `price * (1 + rate)` になっており割引ではなく値上げになっている。
apply_tax() は `price * (1 - tax_rate)` になっており税込みではなく税引きになっている。

（スキルなしのため Issue 起票・構造化レポート・自己修復ループなし。分析のみ）
