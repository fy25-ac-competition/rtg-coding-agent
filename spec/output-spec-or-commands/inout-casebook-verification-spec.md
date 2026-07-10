# In/Out 事例集 検証 spec（spec 全文 / コマンド列の実出力カタログ化）

**バージョン**: v1.0.0 / **作成日**: 2026-07-10 / **対象リポジトリ**: rtg-coding-agent
**対象ブランチ**: `feature/output-spec-or-commands`
**位置づけ**: [output-spec-or-commands-spec.md](output-spec-or-commands-spec.md)（2形式ポリシー本体）と
[commands-format-stability-fix-spec.md](commands-format-stability-fix-spec.md)（commands安定化の追加修正）は
**実装済み・検証済み**。本specはその**現状実装（変更しない）に対して、実際に「どのプロンプトに対して
どんな spec 全文 / コマンド列が出るか」を観測し、In/Out 事例集としてカタログ化する**ための検証手順である。
バグ探しではなく **characterization（現状の実出力の記録）** が目的。

---

## この spec の読み進め方

本ファイルを上から下に読み進めて作業すれば、「入力プロンプト集の把握」→「分類ルールの理解」→
「実行（`auto-pytest-reporter` skill 経由）」→「In/Out 事例集レポートの作成」まで一気通貫で完了する。

---

## 1. 背景・目的

`rtg-coding-agent` の `src/agents/coding_agent.py` の `_INSTRUCTION` は、RTG から届く質問テキストの
種別によらず、応答を必ず次の2形式のいずれか一方に強制する：

- **spec 形式**: Markdown（`## 実現方針` / `## 変更範囲` / `## 手順` の3セクション構成）
- **commands 形式**: 1行1コマンドの生テキスト（説明・番号・コードフェンス無し）

利用者から「実際にどんなプロンプトを投げるとどんな spec 全文 / コマンド列が返ってくるのか、
具体的な In/Out の事例集を見たい」という要望があった。既存2spec（本体・安定化修正）は
「形式が2つのいずれかに収まるか」「マッピング精度」を検証済みだが、**実際の出力全文を
恒久的な記録として残すもの**ではなかった。本specはこのギャップを埋める。

**対象外（本specでは変更しない）**: `_INSTRUCTION` を含む `src/` 配下の実装一式、
`src/schemas/a2a.py`、`src/routers/a2a.py`。これらは読み取り専用の前提として扱う。

---

## 2. 検証範囲（入力プロンプト集）

RTG の7メソッド（[README.md](../../README.md) 「CA メソッド対応表」）のうち、
**「元々 spec 全文または commands を生成する目的だった」3メソッド**
（`create_spec` / `edit_spec` / `generate_command_list`）は**各2プロンプト**、
**残り4メソッド**（`investigate_impact` / `notify_approval` / `notify_rejection` / `suggest_usecases`）は
**各1プロンプト**とする。合計 **10 プロンプト**。各プロンプトは **1回のみ** 実行する
（LLMは非決定的だが、事例集としては代表1事例で十分という利用者判断）。

全ケース **`project_id=None`**（GCS/demo アプリ探索ツール経路は対象外。利用者判断により、
探索ツールが実際に呼ばれる事例は本カタログには含めない。該当ケースでは探索ツールは
「対象アプリが指定されていないため探索できません」を返し、LLM は一般論で回答する）。

### 2.1 プロンプト表

| case_id | メソッド | 期待形式 | プロンプト全文 |
|---|---|---|---|
| `create_spec-1` | create_spec | spec | `以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\nカート画面にクーポン機能を追加したい` |
| `create_spec-2` | create_spec | spec | `以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\n商品一覧画面にカテゴリ絞り込み検索を追加したい` |
| `edit_spec-1` | edit_spec | spec | 下記2.2 参照（クーポン spec への「有効期限」追加） |
| `edit_spec-2` | edit_spec | spec | 下記2.2 参照（カテゴリ検索 spec への「並び替え」追加） |
| `generate_command_list-1` | generate_command_list | commands | 下記2.2 参照（クーポン spec からコマンド列生成） |
| `generate_command_list-2` | generate_command_list | commands | 下記2.2 参照（カテゴリ検索 spec からコマンド列生成） |
| `investigate_impact-1` | investigate_impact | spec | `以下のコマンドが対象システムに与える影響を、実現方針/変更範囲/手順の枠組みで報告してください。\n--- コマンド ---\nALTER TABLE orders ADD COLUMN coupon_id INTEGER;` |
| `notify_approval-1` | notify_approval | commands | `以下のコマンドが承認されました。模擬実行し、実行したコマンドの一覧を報告してください。\n--- コマンド ---\ngit checkout -b feature/coupon\ntouch coupon_service.py\npytest tests/test_coupon_service.py -v` |
| `notify_rejection-1` | notify_rejection | spec | `以下のコマンドは拒否されました。実行しないでください。\n--- コマンド ---\ngit push --force origin main` |
| `suggest_usecases-1` | suggest_usecases | spec | `以下の対象ソースを分析し、ユーザーが「変更したいこと」の候補を2〜3件、1行1件で列挙してください。\n--- 対象ソース ---\n（対象アプリ未指定。一般的なECサイトのカート機能を前提に候補を提示してください）` |

> 期待形式は [output-spec-or-commands-spec.md §2.3](output-spec-or-commands-spec.md#23-全リクエストを受理し2形式へ強制マッピング) の
> マッピング表に準拠。`generate_command_list` と `notify_approval` のみ commands、他は spec。

### 2.2 edit_spec / generate_command_list のプロンプト全文（現行specを含むため長文）

**`edit_spec-1`**:
```
以下の現行 spec を、追加要望に応じて更新し、更新後の spec 全文（Markdown・実現方針/変更範囲/手順）を返してください。
--- 現行spec ---
# spec: クーポン機能

## 実現方針
カート画面にクーポンコード入力欄を追加し、入力されたコードを検証して合計金額に割引を適用する。

## 変更範囲
- cart.html: クーポン入力欄の追加
- cart.js: クーポン検証・割引計算ロジックの追加
- coupon_service.py: クーポンコードの検証API

## 手順
1. cart.html にクーポン入力欄と適用ボタンを追加する
2. cart.js に適用ボタンのイベントハンドラを追加する
3. coupon_service.py にクーポンコード検証関数を実装する
4. 割引適用後の合計金額をカート画面に反映する
--- 追加要望 ---
クーポンに有効期限を設定できるようにしたい。期限切れのクーポンはエラーメッセージを表示して適用しない。
```

**`edit_spec-2`**:
```
以下の現行 spec を、追加要望に応じて更新し、更新後の spec 全文（Markdown・実現方針/変更範囲/手順）を返してください。
--- 現行spec ---
# spec: カテゴリ絞り込み検索

## 実現方針
商品一覧画面にカテゴリ選択のドロップダウンを追加し、選択したカテゴリに一致する商品のみを表示する。

## 変更範囲
- product_list.html: カテゴリ選択ドロップダウンの追加
- product_list.js: カテゴリ選択時の絞り込みロジック
- product_service.py: カテゴリ条件付き商品取得API

## 手順
1. product_list.html にカテゴリ選択ドロップダウンを追加する
2. product_list.js にドロップダウン変更イベントのハンドラを追加する
3. product_service.py にカテゴリ条件でフィルタする関数を実装する
4. 絞り込み結果を一覧に反映する
--- 追加要望 ---
絞り込んだ商品一覧を、価格の安い順・高い順に並び替えられるようにしたい。
```

**`generate_command_list-1`**:
```
以下の spec を実現するために実行すべきコマンドを、実行順に列挙してください。
--- spec ---
# spec: クーポン機能

## 実現方針
カート画面にクーポンコード入力欄を追加し、入力されたコードを検証して合計金額に割引を適用する。

## 変更範囲
- cart.html: クーポン入力欄の追加
- cart.js: クーポン検証・割引計算ロジックの追加
- coupon_service.py: クーポンコードの検証API

## 手順
1. cart.html にクーポン入力欄と適用ボタンを追加する
2. cart.js に適用ボタンのイベントハンドラを追加する
3. coupon_service.py にクーポンコード検証関数を実装する
4. 割引適用後の合計金額をカート画面に反映する
```

**`generate_command_list-2`**:
```
以下の spec を実現するために実行すべきコマンドを、実行順に列挙してください。
--- spec ---
# spec: カテゴリ絞り込み検索

## 実現方針
商品一覧画面にカテゴリ選択のドロップダウンを追加し、選択したカテゴリに一致する商品のみを表示する。

## 変更範囲
- product_list.html: カテゴリ選択ドロップダウンの追加
- product_list.js: カテゴリ選択時の絞り込みロジック
- product_service.py: カテゴリ条件付き商品取得API

## 手順
1. product_list.html にカテゴリ選択ドロップダウンを追加する
2. product_list.js にドロップダウン変更イベントのハンドラを追加する
3. product_service.py にカテゴリ条件でフィルタする関数を実装する
4. 絞り込み結果を一覧に反映する
```

---

## 3. 分類ルール（`classify_output` の仕様）

実出力テキストを次の3分類のいずれかに機械判定する。テストハーネス（`tests/test_inout_cases.py`）内の
`classify_output(text) -> str` として実装する。

| 分類 | 判定条件 |
|---|---|
| `spec` | `## 実現方針` / `## 変更範囲` / `## 手順` の3見出しのうち**2つ以上**を含む |
| `commands` | 上記 spec 見出しを**1つも含まず**、かつ `list_project_files(` / `read_project_file(` / `search_project_code(` の**いずれも含まない**（ツール名リーク無し） |
| `other` | 上記どちらにも該当しない（報告文・拒否確認文・候補列挙・コードフェンスで全体を囲んでいる 等） |

`other` と判定された場合、さらに以下のサブラベルを付与し記録する（事例集の観測メモに使う）：

- `tool-name-leak`: `list_project_files(` 等のツール呼び出し疑似構文を含む
- `spec-refusal`: 「実行権限がない」「機能範囲外」等、能力の限界を理由にした拒否文言を含む
- `unclassified`: 上記いずれでもない

---

## 4. 実行方法（重要: 本リポジトリ固有の前提）

**注意**: `auto-pytest-reporter` skill の既定前提（`src/venv/bin/python`・`src/` を cwd に
`pytest.ini` の `testpaths=tests` 経由で実行）は、**本リポジトリでは成立しない**。
本リポジトリは次の構成である：

- venv はリポジトリ**ルート**の `venv/`（`src/venv` ではない）。Python バイナリ:
  `venv/bin/python`（Unix/Mac）/ `venv\Scripts\python.exe`（Windows）。
- pytest 実行は**リポジトリルートを cwd** として行う（`src/` ではない）。
  本specの工程で `pytest.ini`（ルート直下）を新規作成し、`testpaths = tests`・
  `pythonpath = .`・`markers = e2e: 実 Vertex AI 呼び出しを伴う検証用マーカー` を定義する。
- 本ハーネス（`tests/test_inout_cases.py`）は `@pytest.mark.e2e` を付与し、
  **`google.*` のスタブ化を行わない**（実 Vertex AI を呼ぶことが目的のため）。
  venv には `google-adk` / `google-genai` が導入済みであることを前提とする。

### 4.1 環境変数（`.env` が無いため inline 指定）

```bash
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=vertex-and-gemini-usage-test
export GOOGLE_CLOUD_LOCATION=us-central1
```

ADC（`gcloud auth application-default login` 済みの認証情報）が利用可能であることが前提。
未認証の場合はユーザーに通知し中断する。

### 4.2 実行コマンド

```bash
cd rtg-coding-agent   # リポジトリルート
./venv/bin/python -m pytest tests/test_inout_cases.py -m e2e -v
```

- `test_target` としては `tests/test_inout_cases.py -m e2e` を指定する
  （`tests/` 全体を対象にすると既存の非 e2e テストも混ざるため、本ケースでは対象を絞る）。
- 429 (`RESOURCE_EXHAUSTED`) 等のレート制限エラーはハーネス内で `pytest.skip` する
  （環境要因であり、アプリ側バグと誤判定しない）。

---

## 5. 合否基準

### 5.1 主基準: 2形式不変条件

各ケースの出力が `classify_output` で `spec` または `commands` のいずれかに分類されること
（`other` が **0件** であること）。これは既存2spec（本体・安定化）が既に保証している
はずの不変条件であり、本ハーネスでも hard assert する。

### 5.2 従基準: 期待マッピングとの一致（観測記録・非 hard assert）

各ケースの実出力形式が、2.1 の「期待形式」列と一致するかどうかを記録する。
**不一致であっても pytest を失敗させない**（事例集収集を主目的とするため、1回のみの
試行でのマッピングの揺れによって収集自体が止まらないようにする）。ただし不一致が
あった場合は正直に記録し、事例集レポートに明記する。

### 5.3 環境要因の除外

`429 RESOURCE_EXHAUSTED` 等の環境要因エラーはテスト対象システムのバグではないため、
`pytest.skip(...)` として扱い、失敗にはしない。

---

## 6. format 違反時の扱い（`auto-pytest-reporter` skill への指示）

- 5.1（2形式不変条件）が満たされない、すなわち `other` 判定が発生した場合、それは
  **アプリ側（`_INSTRUCTION`）の挙動観測**である。テストコード（判定ロジック・アサーション）を
  緩めて握りつぶさないこと。実装（`src/agents/coding_agent.py` 等）も本specの範囲では
  修正しないこと（既存2spec側の追加課題として切り出す）。
  Issue 化が必要と判断した場合は、skill の通常フロー（Issue ドラフト生成→ユーザー承認）に従う。
- テストコード自体の欠陥（import ミス・分類ヒューリスティックのタイプミス等）のみ、
  skill の自己修復（最大5回リトライ、`tests/` 配下のみ変更）の対象とする。
- 5.2（期待マッピング不一致）は失敗として扱わない（上記5.2参照）。observational な記録に留める。

---

## 7. In/Out 収集の仕組み

各テストケースは、実行結果を `.steering/output-spec-or-commands/cases/<case_id>.md` に
以下の形式で書き出す（ハーネスが自動生成）：

```markdown
# <case_id>

- **メソッド**: <method>
- **期待形式**: <expected_format>
- **実出力分類**: <spec|commands|other>
- **サブラベル**: <該当時のみ tool-name-leak / spec-refusal / unclassified>
- **一致**: <true|false>

## 入力プロンプト

<prompt 全文>

## 出力全文

<run_query() が返したテキスト全文>
```

---

## 8. 完了条件

- [ ] `tests/test_inout_cases.py` が新規作成され、10ケースが `@pytest.mark.e2e` で
      parametrize されている。
- [ ] `pytest.ini`（ルート直下）が新規作成され、`e2e` マーカーが登録されている。
- [ ] `./venv/bin/python -m pytest tests/test_inout_cases.py -m e2e -v` が実行され、
      5.1（2形式不変条件）が全ケースで成立している（`other` 0件。ただし個別ケースが
      429 で skip された場合はその旨が記録されている）。
- [ ] `.steering/output-spec-or-commands/cases/` に10件の In/Out ファイルが生成されている。
- [ ] `.steering/output-spec-or-commands/` にテスト実行レポート（`auto-pytest-reporter` 出力）と、
      本カタログを集約した `InOut-Casebook_YYYYMMDD.md` の両方が存在する。
- [ ] `git diff --stat` で `src/`・`schemas`・`routers` に差分が無いこと
      （変更対象は `spec/`・`tests/`・`pytest.ini`・`.steering/` のみ）。

---

## 9. 参照ファイル一覧

### 変更対象（本spec範囲）

| ファイル | 変更種別 |
|---|---|
| `tests/test_inout_cases.py` | 新規（10ケースの e2e In/Out 収集ハーネス） |
| `pytest.ini` | 新規（`e2e` マーカー登録） |
| `.steering/output-spec-or-commands/cases/*.md` | 新規（テスト実行時の自動生成） |
| `.steering/output-spec-or-commands/TestReport_*.md` | 新規（`auto-pytest-reporter` 出力） |
| `.steering/output-spec-or-commands/InOut-Casebook_*.md` | 新規（事例集レポート） |

### 参照のみ（変更しない）

| ファイル | 確認内容 |
|---|---|
| `src/agents/coding_agent.py` | `run_query()` / `_INSTRUCTION`。本specはこれを**呼び出すのみ**で変更しない |
| `src/agents/tools.py` / `src/services/gcs_client.py` | GCS探索ツール（全ケース project_id=None のため未使用経路） |
| `src/routers/a2a.py` / `src/schemas/a2a.py` | A2A ワイヤ形式（本specでは経由しない。`run_query` を直接呼ぶ） |
| `README.md` | 「CA メソッド対応表」（質問テキスト先頭パターンの出典） |
| `spec/output-spec-or-commands/output-spec-or-commands-spec.md` | 2形式ポリシー本体 |
| `spec/output-spec-or-commands/commands-format-stability-fix-spec.md` | commands安定化の追加修正（診断・合格実績の出典） |
