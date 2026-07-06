---
name: spec-compliance-review
description: >
  実装ファイルと detail-spec を突き合わせて仕様適合性検証レポートを .steering/ に生成する。
  「spec 適合性を確認して」「compliance レポートを作って」「仕様と突き合わせて」
  「実装が仕様通りか検証して」「handoff 前にチェックして」「G-V を検証して」
  「RoleB を検証して」「B-3 のレポートを出して」と言われたら迷わずこのスキルを使うこと。
  タスク完了後・handoff 前・結合テスト前・フェーズ完了前に実行する。
---

# spec-compliance-review

実装が spec を満たしているか体系的に確認し、後続担当が安心して取り込めるレポートを生成する。
「何となく合ってそう」で handoff するより、このスキルで差分を明示した方がチーム全体の手戻りが減る。

## 引数

- `task_id` or `role`: 検証対象（例: B-3, RoleB, A-1, G-V, G-5）
  - タスク ID: 単一タスクを検証
  - ロール名: そのロールの全タスクをまとめて検証
- `output_path`: 出力先（省略時: `.steering/<role-or-phase>/<taskid>-spec-compliance-report.md`）

---

## 手順

### 1. 検証対象の特定

work-assignment.md を以下の優先順で探す:

```
spec/<phase>/work-assignment.md                                  # phase1, phase2
spec/<phase>-debug/<area>/generalization-improvement-spec.md     # debug タスク（G-* など）
spec/<phase>-debug/<area>/detail-spec/<taskid>-*.md              # debug タスク個別 spec
```

見つかったら以下を読み取る:
- タスク定義・成果物ファイルのパス
- 参照すべき detail-spec のパス（実装メモ欄）
- 内包単体テスト観点

ロール単位の場合は全タスクを順番に処理し、最後に総合判定をまとめる。

---

### 2. 実装ファイルの読み込み

実際のコードを読まずに照合はできない。照合前に成果物ファイルを全て読む。

```bash
# 成果物ファイルの存在確認
ls <成果物ファイルのパス>
```

ファイルが存在しない場合は即座に ❌ を宣言し、以下のメッセージを出してストップ:

```
❌ 成果物ファイルが存在しません: <パス>
/implement-task {task_id} で実装を完了させてから再度 /spec-compliance-review を実行してください。
```

---

### 3. 要件別突き合わせ

実装ファイルと detail-spec を照合し、全要件を漏れなく記録する。

照合する観点（優先順）:

1. **シグネチャ** — 関数名・引数名・型アノテーション
2. **戻り値** — キー名・データ型・Optional の有無
3. **エラー処理** — 例外・None・デフォルト値・フォールバック
4. **セキュリティ** — spec に記載があれば必ず確認
5. **ADK パターン** — `LlmAgent` + `output_schema` パターン準拠（`CLAUDE.md` の ADK セクション参照）

---

### 4. テスト結果の確認

```bash
cd src && python -m pytest tests/<phase>/test_<file>.py -v --tb=short 2>&1 | tail -10
```

テストが存在しない・未実行の場合は `/auto-pytest-reporter` を呼んで実行し、その結果をレポートに記録する。テストなしで ✅ は出せない（spec の「内包単体テスト観点」に対応するテストが必要）。

---

### 5. レポート生成

以下の構成でレポートファイルを書き出す。**総合判定を冒頭に置く**ことで、読み手がレポートを開いた瞬間に結論を把握できる。

**出力先**: `.steering/<role-or-phase>/<taskid>-spec-compliance-report.md`
（既存ファイルは上書きする。差分確認は不要）

---

#### レポート構成テンプレート

```markdown
# spec-compliance-review: {task_id}

**検証日**: {日付}  
**ブランチ**: {ブランチ名}  
**検証者**: Claude Code

---

## 総合判定: ✅ 仕様準拠 / ⚠️ 要確認 / ❌ 仕様違反

（根拠を1〜3文で説明）

---

## 要件別突き合わせ表

| spec 要件 | spec 箇所（ファイル:行） | 実装場所（ファイル:行） | 判定 |
|---------|-------------------|-------------------|------|
| ...     | ...               | ...               | ✅/⚠️/❌ |

---

## 意図的逸脱一覧

逸脱がなければ「なし」と記載。

| # | 差分（概要） | spec の記述 | 実装 | 根拠 | 後続への影響 |
|---|------------|------------|------|------|------------|
| 1 | ...        | ...        | ...  | ...  | ...        |

---

## テスト結果サマリー

| テストファイル | 件数 | 結果 |
|-------------|------|------|
| tests/phase2/test_xxx.py | 17件 | ✅ 全件 PASSED |

---

## 後続担当への伝達事項

後続が取り込む際に知っておくべき情報を記録する。なければ「なし」。

| 担当 | 内容 | 優先度 |
|------|------|-------|
| ... | ... | 低/中/高 |
```

---

### 6. 逸脱の扱い

逸脱 = 悪いことではなく、**根拠が記録されていないことが問題**。

- 逸脱が「spec の意図を損なわない」と判断できれば ⚠️（後続への伝達事項に記録）
- 逸脱が「spec の意図を損なう」なら ❌（修正が必要）
- 承認された逸脱は `docs/deviations.md` にも追記する

---

## 総合判定の基準

| 判定 | 条件 |
|------|------|
| ✅ 仕様準拠 | 全要件が満たされている（意図的逸脱があっても根拠が明示されている）。テスト全件 PASSED |
| ⚠️ 要確認 | 軽微な差異があるが spec の意図は満たしている。後続担当への伝達が必要 |
| ❌ 仕様違反 | 要件を満たしていない箇所がある、またはテストが失敗している |

---

## 結果による次のアクション案内

**✅ または ⚠️ の場合**:

```
✅ レポート生成完了: .steering/<role>/<taskid>-spec-compliance-report.md

次のステップ:
  /handoff-sync {task_id}   ← shared hub へのマージ手順と下流通知
```

**❌ の場合**:

```
❌ 仕様違反があります。handoff 前に修正が必要です。

修正手順:
  1. レポートの「要件別突き合わせ表」の ❌ 行を確認
  2. /implement-task {task_id} で該当箇所を修正
  3. 修正後に再度 /spec-compliance-review {task_id} を実行
```

---

## 使用例

```
/spec-compliance-review B-3
/spec-compliance-review RoleB
/spec-compliance-review A-1 .steering/RoleA/a1-report.md
/spec-compliance-review G-V
/spec-compliance-review G-5
```
