# テスト実行レポート: test_calc_broken_assertion（自己修復）

## 1. メタデータ
- **実行日時**: 2026-06-21 (eval iteration-1)
- **対象スクリプト**: `.claude/skills/open-github-issue-workspace/fixtures/test_calc_broken_assertion.py`
- **テスト指示書**: 「target_calc.py の add/multiply/divide 関数が仕様通りに動作することを確認するテスト。すべてのテストがPASSすることを期待する。2+3=5、10÷2=5.0 が正しい結果。」
- **最終ステータス**: **SUCCESS**
- **リトライ回数**: 1 / 5

## 2. テストの目的
`target_calc.py` の `add()`・`multiply()`・`divide()` 関数が正しく動作することを確認する。

## 3. 実行結果サマリー
初回実行で 2 件失敗したが、原因がテストコード側の誤アサーションと判定し修正（リトライ 1 回）。
修正後の再実行で全5テスト PASS。**`target_calc.py`（アプリ本体）は一切変更していない。**

## 4. 自己修復ログ

| 回数 | 修正ファイル | 修正内容 | 結果 |
|------|------------|----------|------|
| 1 | `test_calc_broken_assertion.py` | `test_add_positive`: `== 99` → `== 5`（2+3の正解は5）<br>`test_divide_normal`: `== 9.9` → `== 5.0`（10÷2の正解は5.0）| PASS |

**判定根拠**:
- `add(2, 3)` の結果は `5`（`target_calc.py` の実装は正しい）にもかかわらず `== 99` と比較していた → テストコードの誤り。
- `divide(10.0, 2.0)` の結果は `5.0`（正しい）にもかかわらず `== 9.9` と比較していた → テストコードの誤り。
- `target_calc.py` の実装はいずれも仕様通りであり、修正対象はテストコードのみと判断。

## 5. ログ参照

<details><summary>初回実行ログ（FAILED）（クリックして展開）</summary>

```text
FAILED test_calc_broken_assertion.py::test_add_positive
  assert 5 == 99  where 5 = add(2, 3)

FAILED test_calc_broken_assertion.py::test_divide_normal
  assert 5.0 == 9.9  where 5.0 = divide(10.0, 2.0)

2 failed, 3 passed in 0.09s
```

</details>

<details><summary>修正後リトライログ（PASSED）（クリックして展開）</summary>

```text
test_calc_broken_assertion.py::test_add_positive PASSED [ 20%]
test_calc_broken_assertion.py::test_add_negative PASSED [ 40%]
test_calc_broken_assertion.py::test_multiply PASSED [ 60%]
test_calc_broken_assertion.py::test_divide_normal PASSED [ 80%]
test_calc_broken_assertion.py::test_divide_by_zero PASSED [100%]

5 passed in 0.05s
```

</details>

## 6. アクションアイテム
テストコードの誤アサーションを修正して PASS に到達したため、GitHub Issue は作成しない。
