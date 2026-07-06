---
name: handoff-sync
description: >
  タスク完了時に共有ハブ（feature/phaseXX）へのマージ手順と下流担当への完了通知を案内し、
  ユーザーが依頼すれば実際にマージ・プッシュまで実行する。
  「handoff して」「B-3 を共有ハブに上げて」「マージの手順を教えて」「下流に通知して」
  「feature/phase02 にマージして」「次の担当に引き継いで」「feature/phaseXX にマージして」
  「push して」と言われたら迷わずこのスキルを使うこと。
  DoD を達成したタスクを shared hub に上げるとき、また下流担当への取り込み手順が必要なときに使う。
---

# handoff-sync

DoD を確認し、shared hub へのマージ・プッシュ・下流通知を一括で処理する。
「とりあえず push しておく」より handoff の型を守る方が、後続のコンフリクトと手戻りを防ぐ。

## 引数

- `task_id`: handoff するタスク ID（例: B-3、G-V。省略時は会話コンテキストから判断）
- `hub_branch`: 共有ハブのブランチ名（省略時: `CLAUDE.md` の Git フローセクションまたは `git log` から自動判定。例: `feature/phase02`）

---

## 手順

### 1. 現在のブランチとステータスの確認

```bash
git branch --show-current   # 作業ブランチを把握
git status --short          # 未コミットの変更がないか確認
```

未コミットの変更がある場合は先にコミットするよう促す。

hub_branch が不明な場合は `CLAUDE.md` の「Git フロー」セクションを参照するか、
`git log --oneline origin/feature/phase02` 等で共有ハブを特定する。

---

### 2. DoD 事前確認

以下を確認する。未完了があれば handoff をストップして必要な作業を案内する。

- [ ] **テスト**: 最後に実行したテストが全件 PASSED（`auto-pytest-reporter` の結果、または直近の pytest 実行で確認）
- [ ] **spec 逸脱**: 逸脱があれば `docs/deviations.md` に記録済み
- [ ] **レポート**: `.steering/` に `spec-compliance-review` レポートがある、または総合判定 ✅/⚠️ が確認できる

> レポートがない場合の代替確認: テスト件数が spec の「単体テスト観点」を網羅していれば DoD OK と判断してよい。
> ドキュメント・スキルのみの変更（コードなし）はテストとレポートを不要として扱う。

**DoD 未達の場合**:

```
⛔ {task_id} の handoff を開始できません。
未完了: <未完了の DoD 項目>
  → /implement-task {task_id} または /spec-compliance-review {task_id} で解決してください。
```

---

### 3. マージ実行

ユーザーが「マージして」と依頼した場合はそのまま実行する。手順を提示するだけでは不十分。

```bash
# shared hub へ切り替えて最新を取得
git checkout {hub_branch}
git fetch origin
git pull origin {hub_branch}

# 担当ブランチをマージ（--no-ff でマージコミットを残す）
git merge --no-ff {current_branch} -m "merge: {task_id} 完了（テスト{X}件合格）"

# push
git push origin {hub_branch}
```

#### コンフリクト発生時の対応

コンフリクトが発生したら慌てず以下の順で解消する:

```bash
git status    # コンフリクトファイルの一覧を確認
```

コンフリクトの解消方針（このプロジェクトの場合）:

| コンフリクトの種類 | 方針 |
|-----------------|------|
| import 節（担当ブランチが新しい import を追加） | 両方の import を残す。重複は除去 |
| ロジック追加（互いに独立した追記） | 両方のコードブロックを残す |
| 同一行の変更（競合） | 担当ブランチ側（`>>>>>>`）を優先し、理由をコメントまたは逸脱として記録 |

解消後:

```bash
git add <解消したファイル>
git merge --continue    # コミットメッセージはデフォルトのまま OR 編集
git push origin {hub_branch}
```

---

### 4. 下流担当への完了通知を生成

work-assignment.md の「引き継ぎサマリー表」を参照して通知文を生成する。

```
spec/<phase>/work-assignment.md                                  # 通常
spec/<phase>-debug/<area>/work-assignment.md                     # debug 系
```

通知テンプレート:

```
【{task_id} 完了通知】

▶ 着手可能になったタスク:
  - {next_task}: {next_task_description}

▶ 注意事項（後続担当への伝達）:
  （.steering/ レポートの「後続担当への伝達事項」から転記）

▶ 参照ファイル:
  - .steering/{role}/{taskid}-spec-compliance-report.md
  - docs/deviations.md（逸脱があった場合）
```

下流担当がいない場合（個人開発・フェーズ完了時）はこのステップをスキップしてよい。

---

### 5. 下流担当の取り込み手順を提示

下流担当がこの handoff を取り込む手順（下流担当に共有する）:

```bash
# 下流担当のブランチで実行
git fetch origin
git rebase origin/{hub_branch}

# コンフリクトが出た場合
git status              # コンフリクトファイルを確認
# ... 解消 ...
git add <ファイル>
git rebase --continue
```

---

### 6. 完了メッセージ

```
✅ {task_id} の handoff 完了。

マージコミット: {commit_hash}

自分の次のタスク（{next_task_for_self}）着手前に:
  git fetch origin && git rebase origin/{hub_branch}
を実行して shared hub の最新を取り込んでください。
```

---

## 使用例

```
/handoff-sync B-3
/handoff-sync A-1 feature/phase03
/handoff-sync C-4b
/handoff-sync G-V feature/phase02
```
