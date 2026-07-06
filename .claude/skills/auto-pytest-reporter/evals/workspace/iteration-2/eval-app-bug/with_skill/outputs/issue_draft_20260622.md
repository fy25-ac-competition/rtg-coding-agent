# [Auto-Bug] target_buggy_service: discount/apply_tax の演算子符号が逆転している

## 🚨 バグ概要

- **失敗したテスト**: `test_buggy_service.py` — `test_discount_10_percent`, `test_apply_tax_10_percent`
- **エラーメッセージ（核心）**: `AssertionError: 期待値 900.0、実際 1100.0` / `期待値 1100.0、実際 900.0`
- **最終ステータス**: FAILED（アプリ側バグと判定）

---

## 📋 期待される挙動（Expected Behavior）

- `discount(1000.0, 0.1)` → **900.0**（1000円の10%引き）
- `apply_tax(1000.0, 0.1)` → **1100.0**（1000円に消費税10%を加えた税込み価格）

---

## 💥 実際の挙動・エラー内容（Actual Behavior / Error）

- `discount(1000.0, 0.1)` → **1100.0**（10%引きではなく10%増になっている）
- `apply_tax(1000.0, 0.1)` → **900.0**（税込みではなく10%引きになっている）

---

## 🔁 再現手順（Steps to Reproduce）

1. リポジトリルートに移動する
2. 以下のコマンドを実行する:
   ```bash
   python -m pytest .claude/skills/auto-pytest-reporter/evals/workspace/fixtures/test_buggy_service.py -v
   ```
3. `test_discount_10_percent` と `test_apply_tax_10_percent` が FAIL する

---

## 📄 スタックトレース / ログ抜粋（Logs）

```text
FAILED test_buggy_service.py::test_discount_10_percent
  assert 1100.0 == 900.0

FAILED test_buggy_service.py::test_apply_tax_10_percent
  assert 900.0 == 1100.0
```

---

## 🤖 AI による原因分析（AI Investigation Notes）

### 調査・リトライ履歴

テストコードは仕様通りに正しく記述されているため、テストコード修正は実施しなかった。

### 推定される根本原因

**ファイル**: `target_buggy_service.py`

| 関数 | バグのある実装 | 正しい実装 |
|------|--------------|-----------|
| `discount(price, rate)` | `return price * (1 + rate)` | `return price * (1 - rate)` |
| `apply_tax(price, tax_rate)` | `return price * (1 - tax_rate)` | `return price * (1 + tax_rate)` |

`discount` と `apply_tax` の演算子符号（`+`/`-`）が入れ替わっている。コピー＆ペーストによる修正漏れの可能性が高い。

---

## 🔗 関連情報

- **テスト指示書**: `target_buggy_service.py の discount() と apply_tax() 関数が仕様通りに動作することを確認するテスト`
- **関連ファイル**: `.claude/skills/auto-pytest-reporter/evals/workspace/fixtures/target_buggy_service.py`（演算子符号バグ）
