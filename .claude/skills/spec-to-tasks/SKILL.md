---
name: spec-to-tasks
description: >
  仕様書（spec/*.md）を読んでチーム作業分担ドキュメント（work-assignment.md）を自動生成する。
  担当者サマリー表・タスク一覧（ID/成果物/優先度/テスト観点/実装メモ）・依存グラフ（mermaid）・
  ガントチャート・担当別キックオフプロンプトを出力する。

  「spec から分担を作って」「work-assignment を生成して」「タスク分解して」
  「担当ごとのキックオフプロンプトを作って」「依存グラフを作って」「ガントを生成して」
  「この spec を担当に割り振って」「実装計画を立てて」と言われたら迷わずこのスキルを使うこと。
  spec ファイルが特定できればフェーズ番号や引数がなくても実行してよい。
---

# spec-to-tasks

仕様書を読んで、チームが並行開発を即日開始できる `work-assignment.md` を一発で生成する。
手打ちで分担を考えるよりも、このスキルで骨格を作ってから微調整する方が速くて漏れが少ない。

生成した `work-assignment.md` は `/implement-task` と `/handoff-sync` の起点になるため、
「実装メモ」欄の正確さが後続スキルの品質を左右する。

## 引数

- `spec_path`（省略可）: 読む spec ファイルのパス（例: `spec/phase3/phase3-spec.md`）
  - 省略時: `spec/<phase>/` 配下の `phase*-spec.md` を自動検出
  - debug/generalization 系: `spec/<phase>-debug/<area>/` 配下を検索

---

## 手順

### 0. 読み込み（必須）

以下の順で読む（コンテキストに既にある場合はスキップ可）:

1. `CLAUDE.md` — プロジェクト規約・ブランチ命名・禁止事項
2. `spec/<phase>/phase*-spec.md` — Source of Truth となる本仕様

   spec の検索順:
   ```
   spec/<phase>/phase*-spec.md
   spec/<phase>-debug/<area>/generalization-improvement-spec.md  # debug 系
   ```
   見つからない場合はユーザーにパスを確認してから進む。

3. `spec/<phase>/detail-spec/*.md` — 存在する場合・担当別詳細仕様

---

### 1. 担当と成果物の整理

spec から以下を抽出する:

- 担当ロール（担当A/B/C/統合 など）とその責務
- 各担当の成果物ファイル（新規 or 変更、ファイルパス付き）
- 担当間の依存関係（handoff が必要なインターフェース・スキーマ）
- 実装ノード ID（N-XX や G-5 など、spec の形式そのままを記録）

---

### 2. `work-assignment.md` に出力する

**出力先**:
- 通常フェーズ: `spec/<phase>/work-assignment.md`
- debug/generalization 系: `spec/<phase>-debug/<area>/work-assignment.md`（既存があればそのパスを優先）

**既存ファイルの扱い**: 既存ファイルが存在する場合は読んだ上で差分を考慮して更新する。
新規の場合はそのまま書き込む。

---

#### a. 担当者サマリー表

| 担当 | ロール | 主担当ノード | 成果物（代表） | 想定時間 |
|------|------|------------|-------------|---------|

ロール・想定時間は spec から読み取れる範囲で埋める。不明な場合は「TBD」と記録。

---

#### b. タスク一覧（担当別）

各タスクに以下を必ず記載する。`実装メモ` 欄は `/implement-task` が参照するため正確に書く:

| 項目 | 内容 |
|------|------|
| タスク ID | 担当略称 + 連番（例: A-1, B-3）または spec 準拠の ID（例: G-5） |
| 担当ノード | 実装対象の spec ノード（例: N-17, N-18） |
| 成果物 | ファイルパス（新規/変更を明記） |
| 単体テスト観点 | 箇条書き 3〜5 点（境界値・例外系を含む） |
| 依存タスク | handoff が必要な前提タスク（なければ「なし」） |
| 優先度 | 🟢 即着手可能 / 🟡 依存あり / 🔴 最優先ブロッカー |
| 実装メモ | **着手時に必ず読む detail-spec のパス**（`/implement-task` がここを参照する） |

`実装メモ` の書き方の例:
```
参照: spec/phase2/detail-spec/essay-eval.md
着手前に読む既存ファイル: src/app/agents/examiner.py
注意: A-1 完了（EssayEvalResult スキーマ確定）後に着手すること
```

---

#### c. 依存グラフ（mermaid flowchart TD）

- 担当またぎの handoff エッジを実線（`-->`）で表示
- 同一担当内の順序依存は破線（`-.->` ）で表示
- 並行実行できるパスが視覚的にわかるよう横並びに配置

---

#### d. ガントチャート（mermaid gantt）

開始日が決まっている場合は `dateFormat YYYY-MM-DD` 形式で日付を記入。
決まっていない場合は `section` 形式で工程順のみを表現し、日付は省略してよい:

```
gantt
  title Phase X 開発スケジュール
  section 担当A
  A-1 スキーマ定義 :a1, 0d, 1d
  section 担当B（A-1 待ち）
  B-1 実装     :b1, after a1, 2d
```

最短完了パス（クリティカルパス）が視覚的にわかることを優先する。

---

#### e. 引き継ぎサマリー表

`/handoff-sync` スキルが参照するテーブル。handoff 時に通知すべき情報を記録する:

| 引き継ぎ元 | 完了通知先 | 着手可能になるタスク | 共有すべき注意事項 |
|-----------|---------|----------------|----------------|

---

#### f. 担当別詳細セクション

各担当のセクションに必ず含める:

**役割の背景**（2〜3文）
- その担当がなぜその役割を持つのか
- 他担当との調整事項・移管された経緯があれば記録

**実装メモ**
- タスクごとに「着手時に読む detail-spec のパス」をパス付きでリスト
- 担当またぎの注意事項（「A-1 完了まで B は evaluate_exam を触らない」等）

**担当別キックオフプロンプト**（コードブロック形式）

各プロンプトに必ず含める:

1. **読むファイルの順序**（`CLAUDE.md` → `phase*-spec.md` → `detail-spec` → `work-assignment.md`）
2. **最初に着手するタスク ID**（明示）
3. **DoD（完了条件）** — 箇条書き
4. **禁止事項** — spec 変更禁止・他担当領域への直接書き込み禁止など

プロンプトはコピペしてそのまま Claude Code に貼れる形式にする。

---

### 3. 最後に宣言する

```
🟢 独立して即着手可能なタスク: A-1, B-1
🔴 最優先ブロッカー（先に完了すべきタスク）: A-1（B/C 担当の依存元）

次のステップ:
  /implement-task <task_id>              ← 各タスクの実装
  /spec-compliance-review <task_id>      ← 実装後の適合性確認
  /handoff-sync <task_id>               ← 完了後の shared hub マージと下流通知
```

---

## 使用例

```
/spec-to-tasks
/spec-to-tasks spec/phase3/phase3-spec.md
/spec-to-tasks spec/phase2/phase2-spec.md
/spec-to-tasks spec/phase2-debug/gcp-generalization/generalization-improvement-spec.md
```
