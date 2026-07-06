## 🚨 バグ概要

- **失敗したテスト**: `test_buggy_service.py` — `test_discount_10_percent`, `test_apply_tax_10_percent`
- **エラーメッセージ（核心の 1 文）**: `AssertionError: 期待値 900.0、実際 1100.0`（discount）/ `AssertionError: 期待値 1100.0、実際 900.0`（apply_tax）
- **最終ステータス**: FAILED（リトライ 0 回／テストコードは正しいためリトライ不要）

---

## 📋 期待される挙動（Expected Behavior）

- `discount(1000.0, 0.1)` → `900.0`（1000円から10%引き = 900円）
- `apply_tax(1000.0, 0.1)` → `1100.0`（1000円に消費税10%加算 = 1100円）
- `discount(500.0, 0.0)` → `500.0`（割引率0%なら変化なし）

---

## 💥 実際の挙動・エラー内容（Actual Behavior / Error）

- `discount(1000.0, 0.1)` → `1100.0`（割引のはずが値上がりしている）
- `apply_tax(1000.0, 0.1)` → `900.0`（税込みのはずが税引きになっている）

---

## 🔁 再現手順（Steps to Reproduce）

1. リポジトリルートに移動する
2. 以下のコマンドを実行する:
   ```bash
   python -m pytest .claude/skills/open-github-issue-workspace/fixtures/test_buggy_service.py -v
   ```
3. 以下のエラーが発生する:
   - `test_discount_10_percent` FAILED
   - `test_apply_tax_10_percent` FAILED

---

## 📄 スタックトレース / ログ抜粋（Logs）

```text
FAILED test_buggy_service.py::test_discount_10_percent
  AssertionError: 期待値 900.0、実際 1100.0
  assert 1100.0 == 900.0

FAILED test_buggy_service.py::test_apply_tax_10_percent
  AssertionError: 期待値 1100.0、実際 900.0
  assert 900.0 == 1100.0

2 failed, 1 passed in 0.08s
```

---

## 🤖 AI による原因分析（AI Investigation Notes）

### 調査・リトライ履歴

| 回数 | 試みた修正（テストコード側） | 結果 |
|------|--------------------------|------|
| — | テストコードは仕様通りに正しく記述されているため、テスト側の修正は試みなかった | — |

> テスト指示書（期待値: 900円・1100円）とテストコードのアサーションが一致しており、テスト側に問題なし。アプリ側バグと即時判定。

### 推定される根本原因

`target_buggy_service.py` に 2 箇所の符号ミスがある。

**バグ 1: `discount()` 関数（13行目）**

```python
# 現状（バグあり）
return price * (1 + rate)   # discount(1000, 0.1) → 1100.0

# 正しい実装
return price * (1 - rate)   # → 900.0
```

**バグ 2: `apply_tax()` 関数（19行目）**

```python
# 現状（バグあり）
return price * (1 - tax_rate)   # apply_tax(1000, 0.1) → 900.0

# 正しい実装
return price * (1 + tax_rate)   # → 1100.0
```

両関数で `+` と `-` の符号が逆転しており、割引が値上がり・税込みが税引きになってしまっている。

---

## 🔗 関連情報

- **テスト指示書**: 「target_buggy_service.py の discount() と apply_tax() 関数が仕様通りに動作することを確認するテスト」
- **関連ファイル**: `.claude/skills/open-github-issue-workspace/fixtures/target_buggy_service.py`（13行目・19行目）
