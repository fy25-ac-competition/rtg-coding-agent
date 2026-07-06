---
name: auto-pytest-reporter
description: >
  findy-hackathon の src/ 配下の pytest テストを自律的に実行し、失敗時はテストコードのみ
  を自己修復（最大 5 回リトライ）、アプリ側バグと判定した場合は Issue 内容を生成・提示して
  ユーザー承認後に GitHub Issue を起票し、最終的に Markdown レポートを .steering/ に出力
  するまでを一貫実行する。
  「テストを動かして結果を報告して」「このテストが落ちる原因を調べて直して」
  「バグを見つけたら Issue を立てて」「テスト結果を .steering/ に残して」と言われたら
  必ずこのスキルを使うこと。単なるコードレビューや仕様確認など、テスト実行を伴わない
  依頼では使わない。
---

# auto-pytest-reporter

src/ の pytest テストを実行し、**テストコードのみ**を自己修復しながら問題を切り分け、アプリ側バグを GitHub Issue として記録するまでを自律実行する。

---

## 引数

| 引数 | 必須 | 説明 |
|------|------|------|
| `test_instruction` | 必須 | テストの目的・合否判断基準を示した指示書（テキストまたはファイルパス） |
| `test_target` | 必須 | pytest に渡すパスまたはマーカー（例: `tests/phase2/role-a`、`-m "not e2e"`、`tests/phase1/test_rank_logic.py`）|
| `report_dir` | 省略可 | レポート出力先（省略時: `.steering/auto-test/`） |

---

## 重要な制約（必ず守ること）

- **修正できるのはテストコード（`src/tests/` 配下）のみ。** `app/`・`routers/`・`agents/`・`services/` など実装ファイルは一切変更しない。これがゲートの独立性を保つ核心。
- アプリ側のバグは修正せず、必ず Issue 化する。
- 環境起因のエラー（Defender SAC・DLL など）はアプリバグと誤判定しない。

---

## Step 1: 入力理解

### 1-a: test_instruction の解決

`test_instruction` はテキスト直書き・ファイルパス・ファイル＋セクション指定の3パターンがある。以下の順で判定する。

#### パターン判定フロー

```
test_instruction の値を見る
│
├─ `.md` / `.txt` などの拡張子を含むファイルパスそのもの
│   例: "hogehoge.md"、"spec/test-plan.md"
│   → ファイルを丸ごと読み込む（全体が instruction）
│
├─ 「<ファイル名>」や "ファイル名" の後に "テストXX" や "section" などセクション指定が続く自然文
│   例: 「hogehoge.md」記載のテスト1-Aを実施して
│        "spec/plan.md" の「シナリオB」を実行して
│   → ファイルを読み込み、指定セクションだけを抽出する（後述）
│
└─ それ以外（テキスト直書き）
    → そのまま instruction として使用する
```

#### ファイル読み込み

- ファイルパスは絶対パスまたはリポジトリルートからの相対パスで解決する。
- ファイルが存在しない場合はユーザーに通知して中断する。

#### セクション抽出（ファイル＋セクション指定の場合）

ファイルを読み込んだ後、セクション指定（「テスト1-A」「シナリオB」など）に対応する見出しブロックを探す。

1. Markdown 見出し（`#` `##` `###` ...）または箇条書き番号（`1-A`、`1.A`、`A-1` など）をスキャンして、指定名に最も近いブロックを特定する。
2. そのブロックの先頭から次の同レベル以上の見出しまでの範囲を抽出する。
3. 合致するブロックが見つからない場合は「セクションが見つかりません」と通知し、ファイル全体を instruction として使用するか、ユーザーに確認する。

> **なぜセクション抽出が必要か**: 一つの Markdown に複数テストケースが並んでいる文書をそのまま渡すと、無関係な手順・期待値が混入し誤採点・誤判定を招く。該当セクションだけを切り出すことで instruction のノイズを排除できる。

### 1-b: 残りの入力を確認

1. 解決済みの `test_instruction`（テキスト）からテストの目的・期待挙動・対象システムを把握する。
2. `test_target` からテスト範囲と実行方式を確認する（pytest パス or マーカー）。
3. テスト対象が E2E（`-m e2e`、`test_e2e_smoke.py`、`run_e2e.py` 等）かどうかを判定し、内部フラグとして保持する。

---

## Step 2: 実行環境の確認

**なぜ activate しないか**: Bash はサブシェルごとに環境がリセットされるため `source activate` が無意味になる。代わりに venv 内の Python バイナリを直接指定する方が確実。

### Python バイナリの決定

```bash
# Windows (PowerShell / Git Bash)
PYTHON="src/venv/Scripts/python.exe"

# Unix / Mac
PYTHON="src/venv/bin/python"
```

OS は `uname -s` または `$OSTYPE` で判定するか、バイナリの存在確認（`test -f src/venv/Scripts/python.exe`）で切り替える。

### カレントディレクトリ

pytest.ini が `src/` にあり `pythonpath = .` / `testpaths = tests` を定義している。
**必ず `src/` をカレントにしてから pytest を実行する。**

```bash
cd src && $PYTHON -m pytest <test_target> -v
```

---

## Step 3: 実行＆ロギング

### 3-a: E2E でない場合（条件付き確認）

非 E2E であっても、テストが VertexAI(ADC) や Firestore エミュレーターに依存していると
準備不足のまま実行してしまい、環境エラーを誤ってアプリバグと判定したり無駄なリトライを
招いたりする。そのため、まず依存を判定してから実行する。

#### 依存の判定

`test_target` のパス・`test_instruction` の記述・テストコード内の以下いずれかの参照を確認する。

| 確認対象 | 判定キーワード |
|---------|--------------|
| import / `FIRESTORE_EMULATOR_HOST` 環境変数 | `firestore`, `FIRESTORE_EMULATOR_HOST` |
| ADK / Gemini / VertexAI 呼び出し | `vertexai`, `genai`, `LlmAgent`, `GEMINI_MODEL` |

判断材料がなく不明な場合は「依存あり」側に倒す（安全側）。

#### 依存あり・または不明の場合 → 実行前にユーザーへ確認

> **実行前にユーザーへ確認する**: 以下の準備状況を確認してから進める。
> 1. Google Cloud ADC 認証（`gcloud auth application-default login`）は完了しているか？
> 2. Firestore エミュレーターの起動が必要か？必要なら 3-b の手順を先に実施する。

#### 純粋なユニットテストで依存なしと確信できる場合 → 直接実行（高速パス）

上記キーワードが一切なく、依存が確実にない場合は確認をスキップする。

```bash
mkdir -p .steering/auto-test/log   # log の置き場（src/ 外で管理）
cd src
LOGFILE="../.steering/auto-test/log/test_$(date +%Y%m%d_%H%M%S).log"
$PYTHON -m pytest <test_target> -v > "$LOGFILE" 2>&1
EXIT_CODE=$?
```

### 3-b: E2E の場合

> **実行前にユーザーへ確認する**: ADC 認証・Docker Desktop 起動・Firestore emulator の準備が整っているか。

```bash
# Firestore emulator 起動（src/ で）
cd src && docker compose up -d
docker compose ps   # "Running" を確認

# シードデータ投入
FIRESTORE_EMULATOR_HOST=localhost:8080 $PYTHON scripts/seed_firestore.py
```

その後 Step 3-a 同様にログ保存して pytest を実行する。

---

## Step 4: 環境問題ガード

ログを解析し、**以下のいずれかに合致する場合はアプリ側バグとみなさない**。Issue を立てず、ユーザーに環境対処を案内して終了する。

| 判定キーワード | 原因 | 推奨対処 |
|--------------|------|---------|
| `cygrpc` / `DLL load failed` / `アプリケーション制御ポリシー` | Windows Defender SAC による DLL ブロック | venv 再構築（[手順](.steering/others/windows-knowledge/windows-defender-pytest-issue.md)） |
| `ModuleNotFoundError` で対象が venv 外のシステムパッケージ | venv 不完全 | `pip install -r requirements-dev.txt` で追加インストール |
| pytest の `collection error` + 原因がインフラ/OS 設定 | 環境問題 | 上記を参照 |
| `docker: command not found` / `Connection refused` (emulator) | Docker 未起動 | Docker Desktop を起動し `docker compose up -d` を再実行 |

環境問題と判定した場合のレポートステータスは `ENV_ERROR`（Issue 化しない）。

---

## Step 5: 評価と分岐

### 5-a: EXIT_CODE=0 → 成功

Step 6（SUCCESS レポート作成）へ進む。

### 5-b: EXIT_CODE≠0 → 失敗

ログを精読し、失敗の責任を判定する。

#### テストコード起因と判定する基準（修正してよい）

- `AssertionError` の原因が期待値・比較式の記述ミス（実装の挙動が仕様と合っているのにテストの書き方がおかしい）
- `ImportError` / `ModuleNotFoundError` でテストファイル内の import パスが間違っている
- `unittest.mock.patch` のパスが誤っている（アプリ側関数は正しいのにモック先が違う）
- `TypeError` / `AttributeError` でテスト側のフィクスチャやヘルパーが誤っている

→ **テストファイル（`src/tests/` 内）のみを修正** し、Step 3 へ戻る（最大 5 回）。修正理由・変更箇所を内部メモとして記録する。

> 5 回到達しても解決しない場合は「根本原因がアプリ側にある可能性が高い」として Step 5-c へ移行する。

#### アプリ側バグと判定する基準（修正しない）

- テストコードは正しく書けているのに、アプリの実装が仕様と異なる挙動をしている
- API のレスポンス形式・ステータスコード・フィールド名が仕様から外れている
- Firestore への書き込み/読み込みロジックにバグがある
- リトライ上限（5 回）に達した

→ Step 5-c へ進む。

### 5-c: GitHub Issue 化

起票直前まで進めてから CLI の未導入・未認証で失敗する無駄を防ぐため、
まず GitHub CLI の状態を自動チェックし、問題があれば早期フォールバックする。

#### 0. GitHub CLI 事前チェック（必須）

```bash
gh --version   # インストール確認
gh auth status # 認証確認
```

- **どちらかが失敗した場合**: 起票を中止し、以下をユーザーに案内する。
  - 未インストール: `winget install --id GitHub.cli` または https://cli.github.com/
  - 未認証: `gh auth login` を実行して GitHub 認証を完了させる。
  - Issue 本文を `<report_dir>/issue_draft_<timestamp>.md` に保存してユーザーに通知し、Step 6（FAILED レポート）へ進む。
- **両方成功した場合**: 以下 1〜5 の起票フローへ進む。

1. [.github/ISSUE_RULES.md](.github/ISSUE_RULES.md) の形式に従って Issue 内容（タイトル＋本文 Markdown）を生成する。
2. **ユーザーに内容を提示し、承認を求める。**
3. 承認されたら `gh issue create` で起票する（[ISSUE_RULES.md](.github/ISSUE_RULES.md) のコマンド例参照）。
4. `gh` で起票に失敗した場合は `<report_dir>/issue_draft_<timestamp>.md` としてファイルに保存し、ユーザーに伝える。
5. Step 6（FAILED レポート作成）へ進む。

---

## Step 6: テスト結果レポート出力

### 出力先

```
<report_dir>/TestReport_{YYYYMMDD}_{テスト名}.md
```

`report_dir` は引数未指定の場合 `.steering/auto-test/`。ファイル名に使う「テスト名」は `test_target` のパス末尾またはモジュール名を短縮して使う。

### レポートフォーマット

```markdown
# テスト実行レポート: {テスト名}

## 1. メタデータ
- **実行日時**: {YYYY-MM-DD HH:MM:SS}
- **対象スクリプト**: `{test_target}`
- **テスト指示書**: `{test_instruction の概要}`
- **最終ステータス**: [SUCCESS | FAILED | ENV_ERROR]
- **リトライ回数**: {N} / 5 回

## 2. テストの目的
{test_instruction から読み取った、このテストが何を担保するための試験かの要約}

## 3. 実行結果サマリー
{SUCCESS: 期待通りに動作した証明。FAILED: どこでどのように失敗したか。ENV_ERROR: 環境問題の概要}

## 4. 自己修復ログ（リトライがあった場合）
| 回数 | 修正ファイル | 修正内容の要約 | 結果 |
|------|------------|--------------|------|
| 1    | tests/xxx.py | アサーションの期待値を修正 | 再失敗 |
| …    | …           | …             | …    |

## 5. ログ参照
- ログファイル: `{LOGFILE}`
<details><summary>ログ抜粋（クリックして展開）</summary>

```text
{重要なスタックトレースやエラーメッセージを抜粋}
```

</details>

## 6. アクションアイテム
{SUCCESS: 「対応不要」。FAILED: 「Issue #XXX を起票済み（または issue_draft_XXX.md を参照）」。ENV_ERROR: 「環境問題のため Issue 未発行。対処方法: ...」}
```

---

## 備考: pytest 実行例

```bash
# ユニット／HTTP 統合（エミュレータ不要・高速）
cd src && $PYTHON -m pytest tests/ -v -m "not e2e"

# 特定フェーズのみ
cd src && $PYTHON -m pytest tests/phase2/ -v

# 特定ファイル
cd src && $PYTHON -m pytest tests/phase1/test_rank_logic.py -v

# E2E（サーバー起動済み＋実 Gemini 必要）
cd src && $PYTHON -m pytest tests/common/test_e2e_smoke.py -v -m e2e
```
