# テスト実行レポート: output-spec-or-commands（instruction 2形式化）

## 1. メタデータ
- **実行日時**: 2026-07-10 00:22:09
- **対象スクリプト**: `tests/test_a2a.py`, `tests/test_instruction.py`, `tests/test_tools.py`
- **テスト指示書**: `spec/output-spec-or-commands/` 配下の spec（概要 + detail-spec/01・02）に基づく実装〜検証。CA の出力を「Markdown spec 全文」または「1行1コマンド」の2形式のみに絞る instruction 改修（`src/agents/coding_agent.py`）の回帰確認
- **最終ステータス**: SUCCESS
- **リトライ回数**: 0 / 5 回

## 2. テストの目的
`src/agents/coding_agent.py` の `instruction` を `_INSTRUCTION` 定数として抽出し、
6種類の出力スタイル（spec作成/編集・コマンド生成・影響調査・模擬実行・拒否通知・ユースケース候補）から
「spec 全文」「コマンド列」の2形式へ強制マッピングするポリシーに書き換えた。この変更が

1. A2A ルーター層（`src/routers/a2a.py`、`src/schemas/a2a.py`）の既存の入出力振る舞いを壊していないこと
2. GCS 探索ツール（`src/services/gcs_client.py` / `src/agents/tools.py`）の挙動に影響していないこと
3. 新しい instruction 文言が「2形式ポリシー」「探索方針の維持」「コードフェンス禁止の維持」「旧6スタイル個別文言の削除」「形式選択の二分判定基準」を満たすこと

を、LLM を実際に呼ばずに（`google.*` を MagicMock でスタブ／`run_query` を `@patch` でモック）静的・単体レベルで担保することが目的。

## 3. 実行結果サマリー
`tests/test_a2a.py`（11件）・`tests/test_instruction.py`（5件・新規）・`tests/test_tools.py`（10件）の
計26件がすべて PASSED（0 failed, 0 error）。

- `test_a2a.py`: A2A JSON-RPC エンドポイントの正常系・異常系（method 不正・parts 空・タイムアウト・
  予期せぬ例外・target_source 解決）が全通過。instruction 変更後も `run_query` の呼び出し規約・
  レスポンス組み立て（`A2AResponse.from_text`）に影響がないことを確認。
- `test_instruction.py`（新規）: `_INSTRUCTION` に spec/commands の2形式が定義され、探索方針・
  コードフェンス禁止指示が維持され、旧6スタイルの個別文言（影響調査報告文・模擬実行結果報告・
  拒否確認文・ユースケース候補列挙の具体的な文言）が完全に削除され、形式選択の判定基準
  （二分規則）が明記されていることを確認。
- `test_tools.py`: GCS 探索プリミティブ（list_files/read_file/search_code）の挙動が
  今回の変更で一切影響を受けていないことを確認（無変更ファイルの回帰確認）。

**環境依存について**: 3ファイルとも `google.*`（`google.adk.*` / `google.genai.*` / `google.cloud.storage`）を
`sys.modules.setdefault(..., MagicMock())` で事前スタブしており、実 Vertex AI・実 GCS への
ネットワークアクセスは一切発生しない。ADC 認証・Firestore emulator 等の外部依存は不要。

## 4. 自己修復ログ（リトライがあった場合）
リトライなし（初回実行で全件 PASSED）。

## 5. ログ参照
- ログファイル: `.steering/auto-test/log/test_20260710_002209.log`

<details><summary>ログ抜粋（クリックして展開）</summary>

```text
collected 26 items

tests/test_a2a.py::test_a2a_spec_creation PASSED                         [  3%]
tests/test_a2a.py::test_a2a_command_list PASSED                          [  7%]
tests/test_a2a.py::test_a2a_with_target_source_metadata PASSED           [ 11%]
tests/test_a2a.py::test_a2a_notify_rejection PASSED                      [ 15%]
tests/test_a2a.py::test_a2a_suggest_usecases PASSED                      [ 19%]
tests/test_a2a.py::test_a2a_no_target_source_means_no_project_id PASSED  [ 23%]
tests/test_a2a.py::test_a2a_non_demo_target_source_means_no_project_id PASSED [ 26%]
tests/test_a2a.py::test_a2a_invalid_method PASSED                        [ 30%]
tests/test_a2a.py::test_a2a_empty_parts PASSED                           [ 34%]
tests/test_a2a.py::test_a2a_agent_timeout PASSED                         [ 38%]
tests/test_a2a.py::test_a2a_agent_unexpected_error PASSED                [ 42%]
tests/test_instruction.py::test_instruction_defines_two_output_formats PASSED [ 46%]
tests/test_instruction.py::test_instruction_keeps_exploration_policy PASSED [ 50%]
tests/test_instruction.py::test_instruction_keeps_no_code_fence_rule PASSED [ 53%]
tests/test_instruction.py::test_instruction_removes_legacy_multi_style_wording PASSED [ 57%]
tests/test_instruction.py::test_instruction_has_format_selection_rule PASSED [ 61%]
tests/test_tools.py::test_list_files_excludes_skip_extensions PASSED     [ 65%]
tests/test_tools.py::test_list_files_empty_bucket_config_returns_empty PASSED [ 69%]
tests/test_tools.py::test_read_file_returns_content PASSED               [ 73%]
tests/test_tools.py::test_read_file_not_found PASSED                     [ 76%]
tests/test_tools.py::test_read_file_too_large PASSED                     [ 80%]
tests/test_tools.py::test_read_file_bucket_unset PASSED                  [ 84%]
tests/test_tools.py::test_search_code_returns_matching_lines PASSED      [ 88%]
tests/test_tools.py::test_search_code_invalid_regex_returns_error_entry PASSED [ 92%]
tests/test_tools.py::test_search_code_respects_max_hits PASSED           [ 96%]
tests/test_tools.py::test_search_code_skips_oversized_files PASSED       [100%]

======================== 26 passed, 1 warning in 0.30s =========================
```

</details>

## 6. アクションアイテム
レベル1: 対応不要。
レベル2/3: 「7. レベル2・3 追加検証」参照。**commands 形式の選択安定性に既知の問題あり**（要instruction再調整の検討）。

**注記（このリポジトリ固有の実行方法）**: 本リポジトリには `src/venv/` や `src/pytest.ini` は無く、
`tests/` はリポジトリルート直下、`from src...` 解決はルートを cwd として実行する構成。
今回は `/Users/watanukigenki/Findyハッカソン/.venv/bin/python3`（pytest 9.1.0・google-adk・fastapi・httpx 導入済み）を
リポジトリルートから実行した。

---

## 7. レベル2・3 追加検証（2026-07-10 実施・実 Vertex AI 呼び出し）

`genki.watanuki@gmail.com`（project: `vertex-and-gemini-usage-test`, region: `us-central1`,
model: `gemini-2.5-flash`）を用いて、実際の Vertex AI 呼び出しを伴う疎通検証を実施した。

### 7.1 実施方法

- **レベル2**: リポジトリ直下に README 手順どおり `venv/`（`.gitignore` 対象）を新規作成し
  `requirements.txt` をフルインストール。`uvicorn src.main:app --port 8001` をホスト上で直接起動。
- **レベル3（docker エミュレーション）**: このマシンには docker・podman・colima・nerdctl・finch のいずれも
  未導入のため、真の docker 実行は不可。代替として、scratchpad にクリーンな隔離 venv
  （python 3.12、Dockerfile 指定の 3.13 とは異なる点に注意）を新規作成し `requirements.txt` を
  `pip install --no-cache-dir` でクリーンインストール（`RUN pip install` 相当）した上で、
  Dockerfile の `CMD`（`uvicorn src.main:app --host 0.0.0.0 --port ${PORT}`）と同一のコマンドを
  実行して疎通確認した（ホスト側ポート 8080 は既存の無関係な java プロセスが専有していたため、
  検証用に 8082 へ変更。アプリ側の挙動には影響しない）。
  **限界**: カーネル/名前空間による真の隔離やベースイメージ（`python:3.13-slim`）そのものは
  再現していない。「クリーンな依存解決」「Dockerfile 起動コマンドでの起動」「実際の A2A 応答」は再現。
  検証後、隔離 venv は削除済み。

### 7.2 結果サマリー（README「CA メソッド対応表」7パターン）

| # | メソッド | 期待形式 | レベル2 | レベル3 |
|---|---|---|---|---|
| 1 | create_spec | spec | ✅ spec | ✅ spec |
| 2 | edit_spec | spec | ✅ spec | ✅ spec |
| 3 | generate_command_list | commands | ⚠️ 不安定（後述） | ⚠️ 不安定（後述） |
| 4 | investigate_impact | spec | ✅ spec | ✅ spec |
| 5 | notify_approval | commands | ⚠️ 不安定（後述） | ⚠️ 不安定（後述） |
| 6 | notify_rejection | spec | ✅ spec | ✅ spec |
| 7 | suggest_usecases | spec | ✅ spec（429リトライ後成功） | ✅ spec |

**spec 側にマッピングされた5パターン（#1,2,4,6,7）は、レベル2・3・全試行を通じて安定して
spec 形式（`## 実現方針`/`## 変更範囲`/`## 手順`）のみを返した。** 旧6スタイルの個別文言
（「了解しました。実行しません。」等の確認文、「〜したい」候補の単純箇条書き、自由形式の
報告文）は一度も出現せず、2形式ポリシーの「禁止スタイルを出さない」という目的は
このカテゴリでは達成できている。

### 7.3 判明した問題: commands 形式（#3, #5）の選択安定性が低い

`generate_command_list`（#3）・`notify_approval`（#5）について、原因切り分けのため
レベル2・3合計で追加試行を行った結果:

| パターン | 試行回数 | commands 形式（正しい） | spec 形式へ誤マッピング | 空応答/エラー |
|---|---|---|---|---|
| #3 generate_command_list | 5回 | 2回 | 2回 | 1回（500・空応答） |
| #5 notify_approval | 2回 | 1回（レベル2） | 1回（レベル3） | 0回 |

- 誤マッピング時も**出力自体は spec 形式の枠内**（`## 実現方針`等の見出し）に収まっており、
  旧6スタイルの自由文は出現しない。→ 「2形式のいずれかのみ」という制約自体は破っていない。
- ただし **commands にマッピングされるべきリクエストが spec 側へ流れる頻度が高く**
  （5試行中2回失敗、うち1回は応答自体が空でHTTP 500）、CA メソッド対応表どおりの
  厳密な形式選択という観点では不安定。
- 同一コード・同一 instruction で、レベル2（ホスト venv）・レベル3（隔離venv）の両方で
  同様の不安定さが再現したため、**環境差異（依存バージョン等）ではなく instruction の
  文面自体に起因する LLM の判断のブレ**と考えられる。
- 仮説: `_INSTRUCTION` の「## 探索方針」（tool 探索を促す記述）が、`generate_command_list`/
  `notify_approval` のような「既に与えられた spec/コマンドをテキストとして処理するだけの
  タスク」でも参照されてしまい、「ファイル作成・実行権限がない」という前提に引きずられて
  spec 形式の説明文へ逃げる、または応答を放棄していると推測される。

### 7.4 推奨アクション（ユーザー判断待ち）

現状の `_INSTRUCTION` は「2形式のいずれかのみを返す」という大枠は達成しているが、
**commands 形式への正しいマッピング率が実測で約43%（3/7試行が成功、他は spec 誤マッピングまたはエラー）**
にとどまり、実運用品質としては改善の余地がある。改善案（未実施・要承認）:

- 「## 探索方針」の適用範囲を「対象アプリのコードそのものを分析する指示」に限定する旨を明記し、
  `generate_command_list`/`notify_approval` のような「既に完結したテキストの変換タスク」には
  適用されないことを instruction 内で明示的に除外する。
- 形式の選び方セクションに「commands 判定時は、たとえ実行権限や探索ツールがなくても、
  spec 記載内容から機械的にコマンド文字列を抽出・列挙すればよく、実行可否を判断・言及しない」
  旨を追記する。

## 8. アクションアイテム（レベル2・3分）
`generate_command_list`/`notify_approval` の commands 形式選択安定性について、
instruction の追加改修要否をユーザーに確認する。
