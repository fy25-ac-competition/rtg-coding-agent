---
name: issue-debug-spec
description: >
  GitHub issue 番号を受け取り、そのバグ修正に必要なデバッグスペックファイルを
  `.steering/phase02/bugfix/` 配下に自動生成するスキル。
  「issue #<番号> のデバッグスペックを作って」「issue 10 を調べてスペック書いて」
  「#8 のバグ修正計画を作成して」「新しいバグが見つかったのでスペックファイル作って」
  のように言われたときは必ずこのスキルを使うこと。
  既存の `.steering/phase02/bugfix/` のファイル群と同じフォーマットで出力する。
---

# issue-debug-spec

GitHub issue からデバッグスペックファイルを生成する。

## 引数

- `issue_number`: GitHub issue 番号（例: `10`、`#10`）
- `repo`: リポジトリ（省略時: カレントリポジトリを `gh repo view --json nameWithOwner` で自動検出）
- `output_path`: 出力先（省略時: `.steering/phase02/bugfix/bugfix-issue-<number>-<slug>.md`）

## 手順

### 1. Issue 情報の取得

```bash
gh issue view <issue_number> --json number,title,body,author,state,labels,createdAt,comments \
  --repo <repo>
```

コメントも含めて全文取得する。スクリーンショットの URL は Markdown の alt テキストや周辺文章から症状を読み取る。

### 2. 関連ファイルの推定

Issue タイトル・本文から以下を推定する:

| キーワード例 | 推定対象ファイル |
|-------------|----------------|
| 道場モード・practice | `routers/practice.py`, `mockups/assets/js/user.js` |
| 試験・exam | `routers/exam.py`, `agents/examiner.py` |
| タグ・tagLabels | `services/tags.py`, `services/learning_resources.py`, `mockups/assets/js/user.js` |
| ダッシュボード | `routers/dashboard.py`, `services/dashboard_service.py` |
| 段位・rank | `services/rank_service.py` |
| 採点・評価 | `agents/examiner_essay.py`, `agents/examiner.py` |
| 分析チャット | `agents/analysis_agent.py`, `routers/analysis.py` |
| 研修推奨 | `agents/training_recommender.py` |
| 危険度判定 | `agents/llm_gatekeeper.py`, `agents/gateway.py` |
| UI・表示・画面 | `mockups/assets/js/*.js`, `mockups/*.html` |

推定ファイルが存在するか `ls src/app/` で確認し、存在するものだけをスペックに記載する。

### 3. 症状の分析

Issue 本文から以下を抽出する:

- **何が起きているか**: ユーザーが観測した症状（例: 「回答欄が表示されない」）
- **期待する動作**: 何が正しい状態か（issue から推定。記載がなければ TBD）
- **再現条件**: どの操作をすると発生するか（フロー）
- **影響範囲**: 本番試験のみ・道場のみ・両方、など

### 4. デバッグスペックファイルの生成

以下のフォーマットで `.steering/phase02/bugfix/bugfix-issue-<number>-<slug>.md` に書き出す。

`<slug>` は issue タイトルを kebab-case の英語 3〜5 語に要約したもの（例: `essay-input-not-shown`）。

---

```markdown
# デバッグスペック — <issue title>

**Issue**: #<number> ([リンク](<github url>/issues/<number>))
**報告者**: <author>
**作成日**: <createdAt の日付>
**ステータス**: <state>
**作業ブランチ候補**: `feature/issue<number>-<slug>`

---

## 1. 問題の概要

<issue 本文から症状を整理して記述。箇条書き可。スクリーンショットがある場合はリンクを転記>

### 期待する動作

<正しい状態を記述。issue に記載がなければ推定で記述し「（推定）」を付記>

---

## 2. 再現手順（調査前推定）

<issue 本文・コメントから再現フローを箇条書きで整理>

1. ...
2. ...
3. ...

---

## 3. 原因調査ガイド

推定される問題箇所を grep/cat で確認するコマンドを列挙する。
調査者はここから着手し、結果を §4 に記入する。

### 3-1. 推定関連ファイル

| ファイル | 推定理由 |
|---------|---------|
| `<path>` | <なぜここが怪しいか> |

### 3-2. 調査コマンド

```bash
# <何を確認するか>
<grep / cat コマンド>
```

---

## 4. 根本原因（調査後に記入）

> ⚠️ 調査前は空欄。調査者が埋める。

---

## 5. 修正方針（仮）

> ⚠️ 原因調査後に確定。以下は推定。

<推定される修正アプローチを記述>

---

## 6. 変更予定ファイル

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `<path>` | 修正/追記/新規 | <TBD> |

---

## 7. 検証方法

### 7-1. 修正確認

```bash
# サーバー起動
cd src
FIRESTORE_EMULATOR_HOST=localhost:8080 uvicorn app.main:app --reload
```

<修正後に確認すべき手順>

### 7-2. 回帰確認

```bash
cd src
source venv/bin/activate
FIRESTORE_EMULATOR_HOST=localhost:8080 python -m pytest tests/ -v --tb=short
```

---

## 8. 完了条件

- [ ] 症状が再現しなくなった
- [ ] 既存テストがすべてグリーン
- [ ] <issue 固有の完了条件>

---

*関連: [Issue #<number>](<github url>/issues/<number>)*
```

---

### 5. 出力確認

ファイルを書き出した後、パスを報告する。

```
✅ デバッグスペックを作成しました:
   .steering/phase02/bugfix/bugfix-issue-<number>-<slug>.md

次のステップ:
  1. §3（調査コマンド）を実行して根本原因を特定
  2. §4 に原因を記入
  3. §5-6 の修正方針・変更ファイルを確定
  4. /implement-task で修正を実施
  5. §8 の完了条件を確認してから PR 作成
```

## 注意事項

- `gh` コマンドが使えない場合は `gh auth login` を促す
- issue 本文に技術的詳細が少ない場合（スクリーンショットのみ等）は、推定を明示して空欄を多くする（後から埋める前提）
- すでに同 issue のスペックファイルが存在する場合は上書き前に確認する
