# テスト実行レポート: calc_self_heal（スキルなし）

## 実行日時
2026-06-21 (eval iteration-1 baseline)

## テスト対象ファイル
`.claude/skills/open-github-issue-workspace/fixtures/test_calc_broken_assertion.py`

## 成功/失敗ステータス
**FAILED** — 2 failed, 3 passed

## ログ抜粋
```
FAILED test_calc_broken_assertion.py::test_add_positive
  assert 5 == 99

FAILED test_calc_broken_assertion.py::test_divide_normal
  assert 5.0 == 9.9

2 failed, 3 passed in 0.09s
```

## 失敗原因の分析
テストコード側の誤アサーション（99、9.9）が原因と思われる。
アプリ実装（target_calc.py）は正しい計算結果を返している。

（スキルなしのため自己修復は実施せず。状況の分析のみ）
