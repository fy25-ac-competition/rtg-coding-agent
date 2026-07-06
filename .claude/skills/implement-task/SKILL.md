---
name: implement-task
description: >
  タスク ID（例: A-1, B-3, C-4b, G-5）を受け取り、「spec 確認 → 依存確認 → 既存コード把握 → 実装 →
  単体テスト作成 → 合格確認 → DoD チェック → コミット」を 1コマンドで一貫実行する。

  「A-1 を実装して」「B-3 やって」「C-4b を進めて」「このタスクを始めて」「次のタスクに取りかかって」
  「実装して」「コーディングして」「タスクをこなして」と言われたら迷わずこのスキルを使うこと。
  タスク ID が会話中に明示されていれば引数なしで実行してよい。
  work-assignment.md が存在するプロジェクトでは、タスク番号が言及された時点でこのスキルを呼ぶこと。
---

# implement-task

spec を確認し、依存が揃ってから実装・テスト・DoD チェック・コミットまで一気通貫で進める。
自分でファイルを探し回るより、このスキルの手順に沿う方が漏れが少なく速い。

## 引数

- `task_id`: 実装するタスク ID（例: B-3, A-2, C-4b, G-5）
  - 省略時: 会話コンテキストまたは `work-assignment.md` から自動判定する
- `spec_path`: detail-spec のパス（省略時: work-assignment.md の「実装メモ」列から自動解決）

---

## 手順

### 1. spec 確認

以下を順番に読む（すでにコンテキストにある場合はスキップ可）:

1. `CLAUDE.md` — プロジェクト規約・命名規則・禁止事項
2. work-assignment.md — タスク定義・成果物・依存・テスト観点・実装メモ

   spec の検索順:
   ```
   spec/<phase>/work-assignment.md           # phase2, phase1 など
   spec/<phase>-debug/*/generalization-improvement-spec.md  # debug タスク
   ```
   どちらにも見つからなければパスをユーザーに確認する。

3. detail-spec（work-assignment.md の「実装メモ」欄のリンク先）— 具体的なコード差分・インターフェース定義

読み終えたら、**タスクが大きい場合のみ**以下を宣言してユーザーの確認を取る（単一ファイル変更・数行の修正なら宣言をスキップして即実装に入ってよい）:

```
【タスク {task_id} 実装計画】
- 成果物: <ファイルパス（新規/変更）>
- テスト: <テストファイル名> に <X> ケース予定
- 依存: <前提タスクの完了確認状況>
```

---

### 2. 依存確認

work-assignment.md の依存グラフを参照し、前提タスクが完了しているか確認する。

確認は以下の順で行う（いずれかで OK と判断できれば次へ進む）:

1. **成果物ファイルの存在確認** — 前提タスクの成果物ファイル（例: `app/services/tags.py`）が存在するかを `ls` で確認。最も確実。
2. **会話・コンテキストの記録** — 会話内に「〇〇完了」の記録がある。
3. **git log** — `git log origin/<hub_branch> --oneline | grep <前提タスク ID>` でマージを確認。

**未完了の依存が見つかった場合**: 実装を開始せずにストップ:

```
⚠️ {task_id} の実装を開始できません。
依存タスク {dep_task_id}（成果物: {dep_file}）が未完了です。
{dep_task_id} の実装・マージが完了してから着手してください。
```

---

### 3. ブランチ確認

正しいブランチで作業しているか確認する。

```bash
git branch --show-current
```

- 担当ブランチ（例: `feature/phase02-<role>`）にいれば OK
- 間違ったブランチにいる場合は `git checkout -b feature/<task_id>-<slug>` でブランチを切る
- すでに適切なブランチがある場合は `git checkout <branch>` で移動する

---

### 4. 既存コードの把握

実装前に**必ず**以下を行う。これにより命名規則・スタイル・インポートパターンが把握でき、
一貫性のない実装を防げる。

1. 成果物ファイルが**既存ファイルの変更**の場合 → そのファイルを全文読む
2. 成果物ファイルが**新規作成**の場合 → 最も似た既存ファイルを1つ読む（例: 同ディレクトリの隣接ファイル）
3. テスト対象のファイルが他から import されている場合 → import 元のインターフェースも確認する

---

### 5. 実装

依存が揃い、既存コードを把握したら実装を開始する。

- 読んだ既存コードのスタイル・命名規則・コメント密度に合わせる
- 成果物ファイルパスは work-assignment.md の「成果物」列に完全に従う
- ADK エージェントは `LlmAgent` + `output_schema` パターン（`CLAUDE.md` の ADK セクション参照）
- spec を変更してはいけない。変更が必要な技術的理由があれば、実装を止めてユーザーに報告する

---

### 6. 単体テスト作成

テストは実装直後（または並行して）書く。後回しにすると実装の欠陥を見逃す。

- detail-spec の「単体テスト観点」を全て網羅する
- 境界値・空データ・例外系を追加（spec より多いカバレッジが望ましい）
- 外部 I/O（Firestore・LLM）は最小限のモックに留める（純粋ロジックを先に切り出す）
- テストファイル: `src/tests/<phase>/test_{実装ファイル名}.py`

テスト作成後、インポートが通るかをまず確認する（フルテスト実行前の早期エラー検出）:

```bash
cd src && python -c "from app.<module> import <Symbol>; print('import OK')"
```

---

### 7. 合格確認（`auto-pytest-reporter` に委譲）

テスト実行・自己修復・合否判定は `/auto-pytest-reporter` スキルに委譲する。

**委譲時の引数**:
- `test_instruction`: タスク {task_id} の目的と DoD（このテストが何を担保するか）
- `test_target`: `tests/<phase>/test_{実装ファイル名}.py`

`auto-pytest-reporter` が環境依存（Vertex AI ADC・Firestore エミュレータ等）を自己判定し、
必要時のみユーザーへ準備確認を求める。純粋なユニットテストなら自動実行する。

#### テスト結果による分岐

**SUCCESS（全件 PASSED）** → ステップ8（DoD チェック）へ

**ENV_ERROR（環境問題）** → `auto-pytest-reporter` の案内をユーザーへ転送して implement-task をストップ

**FAILED（アプリ側バグ）** → 今書いた実装が原因の可能性が高いため、Issue 化の前にユーザーへ選択を求める:

```
⚠️ テストが失敗しています（アプリ実装側の原因）。
  [A] 実装を修正して再実行（推奨: 修正箇所が明確な場合）
  [B] Issue を発行して一旦止める（推奨: 以下のいずれかに該当する場合）
      - コンテキスト残量が 10% 以下
      - クレジット残量が 10% 以下
      - 修正に大きな設計変更が必要
```

[A] を選んだ場合は修正後に再度 `auto-pytest-reporter` を呼ぶ。**implement-task 側の再試行は最大3ラウンドまで**。超えたら自動的に [B]（Issue 発行）へ移行する。

---

### 8. DoD チェック

以下が全て揃っていれば完了を宣言する:

- [ ] 成果物ファイルが work-assignment.md の「成果物」列と一致している
- [ ] 単体テスト全件 PASSED（件数を明記: 例「17件全件 PASSED」）
- [ ] 意図的な spec 逸脱があれば `docs/deviations.md` に追記した
- [ ] 次のタスクまたは handoff 先を把握した

---

### 9. コミット

DoD が揃ったらコミットする（`/commit-message` スキルを使うと形式が統一される）。

コミットメッセージの形式（`CLAUDE.md` 規約）:

```
feat: {task_id} <概要（日本語）>
```

例:
```
feat: B-3 個人ダッシュボード N-19 を実装
test: B-3 ダッシュボード API 統合テスト 17件追加
```

---

### 10. 次のアクション案内

```
✅ {task_id} 完了（テスト {X}件 PASSED ／ auto-pytest-reporter レポート: .steering/auto-test/）

次のステップ:
  /spec-compliance-review {task_id}   ← 適合性レポート生成（handoff 前推奨）
  /handoff-sync {task_id}             ← shared hub へのマージ・下流通知
```

---

## 使用例

```
/implement-task B-3
/implement-task A-1 spec/phase2/detail-spec/exam-format-and-essay.md
/implement-task C-4b
/implement-task G-5
```
