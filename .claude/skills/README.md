# Skills — 使い方ガイド

Claude Code の `/skill-name` で呼び出す定型プロンプト集。  
毎回同じ長いプロンプトを手打ちする代わりに、1コマンドで決まった手順を実行できる。

> 詳細解説: [docs/ai-native-spec-driven-dev/03-skills.md](../../docs/ai-native-spec-driven-dev/03-skills.md)

---

## スキル一覧

| スキル | 呼び出し | 何をするか |
|--------|---------|-----------|
| [`spec-to-tasks`](#spec-to-tasks) | `/spec-to-tasks` | spec → `work-assignment.md` を生成 |
| [`implement-task`](#implement-task) | `/implement-task B-3` | タスクを DoD まで一貫実行 |
| [`spec-compliance-review`](#spec-compliance-review) | `/spec-compliance-review B-3` | 実装を spec と突き合わせてレポート生成 |
| [`handoff-sync`](#handoff-sync) | `/handoff-sync B-3` | shared hub へのマージ手順と下流通知を案内 |
| [`commit-message`](#commit-message) | `/commit-message` | Chris Beams 7ルール準拠のコミットメッセージ生成 |
| [`auto-pytest-reporter`](#auto-pytest-reporter) | `/auto-pytest-reporter` | pytest 実行 → 自己修復 → バグ Issue 自律起票 |
| [`skill-creator`](#skill-creator) | `/skill-creator` | 新しいスキルを作成・改善する |

---

## 標準ワークフロー

フェーズ開始から handoff まで、スキルを以下の順で使う:

```
① spec 凍結後
    /spec-to-tasks                    → work-assignment.md を生成

② 各タスク実装時
    /implement-task B-1               → spec 確認・実装・テスト・DoD チェック

③ handoff 前（推奨）
    /spec-compliance-review B-1       → .steering/ に仕様適合性レポートを生成

④ DoD 達成後
    /handoff-sync B-1                 → shared hub へのマージ手順と下流通知を生成

⑤ コミット時（任意）
    /commit-message                   → Chris Beams 準拠のメッセージを生成
```

---

## spec-to-tasks

**spec から `work-assignment.md` を自動生成する。**  
フェーズ開始時に1回だけ実行する。

### 生成物

- 担当者サマリー表（担当 / ロール / 成果物 / 想定時間）
- タスク一覧（ID / ノード / 成果物 / 単体テスト観点 / 依存 / 優先度）
- 担当別の役割の背景・実装メモ
- 依存グラフ（mermaid flowchart TD）
- ガントチャート（mermaid gantt）
- 引き継ぎサマリー表
- 担当別キックオフプロンプト（コピペ即使用）

### 使い方

```
# spec を自動検出して実行
/spec-to-tasks

# spec ファイルを明示して実行
/spec-to-tasks spec/phase3/phase3-spec.md
```

### 注意

既存の `work-assignment.md` がある場合は上書きせず差分を提示する。

---

## implement-task

**タスク ID を受け取り「spec 確認 → 依存確認 → 実装 → テスト → DoD チェック」を一貫実行する。**

### 実行ステップ

1. `CLAUDE.md` → `work-assignment.md` → `detail-spec` を順番に読む
2. 前提タスクが shared hub にマージ済みか確認（未完了ならストップ）
3. 既存コードのスタイルに合わせて実装
4. 単体テストを作成（spec 観点を全網羅 + 境界値・例外系を追加）
5. テスト実行コマンドを提示してユーザーに実行依頼
6. 全件 PASSED を確認して DoD チェック → 次のアクションを案内

### 使い方

```
/implement-task B-3
/implement-task A-1 spec/phase2/detail-spec/exam-format-and-essay.md
/implement-task C-4b
```

### 依存未完了時の出力例

```
⚠️ B-3 の実装を開始できません。
依存タスク B-1（weak_point_service.py）が shared hub 未マージです。
B-1 が feature/phase02 にマージされてから着手してください。
```

---

## spec-compliance-review

**実装ファイルと detail-spec を突き合わせて `.steering/` に仕様適合性レポートを生成する。**  
handoff 前・結合テスト前・フェーズ完了前に実行する。

### 生成物（`.steering/<Role>/<taskid>-spec-compliance-report.md`）

- 総合判定（✅ 仕様準拠 / ⚠️ 要確認 / ❌ 仕様違反）
- 要件別突き合わせ表（spec 箇所:行番号 ↔ 実装場所:行番号）
- 意図的逸脱一覧（差分・根拠・後続への影響）
- テスト結果サマリー
- 後続担当への伝達事項

### 使い方

```
# 単一タスクを検証
/spec-compliance-review B-3

# ロール単位でまとめて検証
/spec-compliance-review RoleB

# 出力先を指定
/spec-compliance-review A-1 .steering/RoleA/a1-report.md
```

---

## handoff-sync

**DoD を確認し、shared hub へのマージ手順・下流担当への通知・下流の取込手順を一括で案内する。**

### 実行ステップ

1. 単体テスト PASSED / 逸脱記録 / compliance レポートを確認（未完了ならストップ）
2. マージコマンドをユーザーに提示（自動実行しない）
3. 下流担当への完了通知文を生成（work-assignment.md の引き継ぎサマリーから抽出）
4. 下流担当が取り込む手順を提示

### 使い方

```
/handoff-sync B-3

# 共有ハブブランチを明示
/handoff-sync A-1 feature/phase03
```

### DoD 未達時の出力例

```
⛔ B-3 の handoff を開始できません。
未完了: 単体テストが未実行です。
完了してから再度 /handoff-sync B-3 を実行してください。
```

---

## commit-message

**Chris Beams の7つのルールに従ってコミットメッセージを作成する。**  
ブランチ名から JIRA ID を自動検出し、`/tmp/commit-message.txt` に書き出してクリップボードにコピーする。

### 7ルール（要点）

1. サブジェクトと本文を空行で区切る
2. サブジェクトは50文字以内（上限72文字）
3. 先頭は大文字
4. 末尾にピリオドを付けない
5. 命令形で書く（"Add" / "Fix" / "Remove"）
6. 本文は72文字で折り返す
7. 本文には「何を・なぜ」を書く（「どうやって」は書かない）

### 使い方

```
/commit-message
```

---

## auto-pytest-reporter

**pytest テスト実行 → 自己修復 → バグ Issue 起票を自律実行する。**  
テストコードのみを自己修復（最大 5 回）し、アプリ側バグは承認後に GitHub Issue として起票、結果を `.steering/` にレポート出力する。

### 実行ステップ

1. テスト指示書と対象ファイルを読み込み、テスト範囲を把握
2. `src/venv` の Python を使って `python -m pytest <target> -v` を実行・ログ保存
3. 失敗がテストコード側の誤り（誤アサーション・import ミス等）なら**テストのみ修正**して再実行
4. アプリ側バグと判定したら Issue 内容を生成 → ユーザー承認後 `gh issue create` で起票
5. `.steering/auto-test/TestReport_*.md` にレポートを保存

### 使い方

```
/auto-pytest-reporter
```

引数（スキル呼び出し後の会話で渡す）:

| 引数 | 説明 |
|------|------|
| `test_instruction` | テストの目的・期待挙動。テキスト直書き・ファイルパス・ファイル＋セクション指定の3形式に対応（後述） |
| `test_target` | pytest パスまたはマーカー（例: `tests/phase2/role-a`、`-m "not e2e"`）|
| `report_dir` | レポート出力先（省略時: `.steering/auto-test/`） |

#### test_instruction の指定形式

**① テキスト直書き**（従来通り）

```
test_instruction: 「add/multiply/divide 関数が仕様通りに動作すること。2+3=5、10/2=5.0 を期待する。」
test_target: tests/phase1/test_calc.py
```

**② Markdown ファイルパス直指定**（ファイル全体を instruction として使用）

```
test_instruction: spec/test-plan.md
test_target: tests/phase2/
```

**③ ファイル＋セクション指定**（複数シナリオが並ぶ文書から1件だけ抽出）

```
test_instruction: 「spec/test-plan.md」記載のテスト1-Aを実施して。
test_target: tests/phase1/test_rank_logic.py
```

- セクション指定は Markdown 見出し（`##`）や番号表記（`1-A`、`A-1` 等）に対応する。
- 指定セクションが見つからない場合はその旨をレポートに記録し、ファイル全体をフォールバック instruction として使用する。

### 注意

- **修正できるのはテストコードのみ**。`app/`・`agents/` 等は一切変更しない。
- Issue 起票前に必ずユーザー承認を求める（自動起票しない）。
- `gh` が未認証の場合は `issue_draft_*.md` にフォールバック。
- Issue 規約: [`.github/ISSUE_RULES.md`](../.github/ISSUE_RULES.md)

---

## skill-creator

**新しいスキルを作成・評価・改善するためのメタスキル。**  
スキルの草案作成 → テスト実行 → 品質評価 → 改善のループを支援する。

### 使い方

```
# 新しいスキルを作りたいとき
/skill-creator

# 既存スキルを改善したいとき
/skill-creator （改善したいスキルの説明を続けて入力）
```

---

## ファイル構成

```
.claude/skills/
├── README.md                      ← このファイル（人間向けインデックス）
├── spec-to-tasks/SKILL.md
├── implement-task/SKILL.md
├── spec-compliance-review/SKILL.md
├── handoff-sync/SKILL.md
├── commit-message/SKILL.md
├── auto-pytest-reporter/
│   ├── SKILL.md
│   └── evals/
│       ├── evals.json             ← eval テストケース定義
│       └── workspace/             ← eval 実行結果・grading・benchmark
└── skill-creator/
    ├── SKILL.md
    └── ...（評価スクリプト・テンプレート等）
```

---

## よくある使い方の組み合わせ

### 新フェーズ開始時

```
# 1. spec を読んでタスク分解
/spec-to-tasks spec/phase3/phase3-spec.md

# 2. 最初のタスクから着手
/implement-task A-1
```

### タスク完了 → handoff

```
# 適合性を確認してからマージ
/spec-compliance-review B-3
/handoff-sync B-3
```

### コミットとセットで

```
# 実装完了後
/implement-task B-3
/commit-message
/handoff-sync B-3
```
