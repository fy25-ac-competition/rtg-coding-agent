# 出力を「spec 全文」または「コマンド列」の2形式のみに絞る調整 spec（概要）

**バージョン**: v1.0.0 / **作成日**: 2026-07-09 / **対象リポジトリ**: rtg-coding-agent
**対象ブランチ**: `feature/output-spec-or-commands`
**詳細 spec**: [detail-spec/01-coding-agent-instruction.md](detail-spec/01-coding-agent-instruction.md) → [detail-spec/02-tests-and-verification.md](detail-spec/02-tests-and-verification.md)

---

## この spec の読み進め方

本ファイル（概要）で方針・工程・参照ファイルを把握したのち、
`detail-spec/01` → `detail-spec/02` の順に**上から下へ**読み進めて作業すれば、
実装（工程1）→ テスト実装（工程2）→ 検証（工程3）まで一気通貫で完了する。

---

## 1. 背景・目的

RTG Coding Agent（CA）は現在、RTG 本体から届く質問テキストの種別に応じて
**6 種類の出力スタイル**を `src/agents/coding_agent.py` の `instruction` で使い分けている
（[README.md](../../README.md) 「CA メソッド対応表」）。

| RTG メソッド | 従来の出力 |
|---|---|
| `create_spec` | Markdown spec 全文 |
| `edit_spec` | 更新後 Markdown spec |
| `generate_command_list` | 1行1コマンド（生テキスト） |
| `investigate_impact` | 影響調査報告文 |
| `notify_approval` | 模擬実行結果報告文 |
| `notify_rejection` | 確認応答テキスト |
| `suggest_usecases` | 1行1件の候補列挙 |

**目的**: CA の出力を、次の **2 形式のいずれか一方のみ**に絞る。それ以外の形式
（報告文・確認応答・候補列挙など）は一切返さないようにする。

- **spec 形式**: Markdown の spec 全文（`## 実現方針` / `## 変更範囲` / `## 手順`）
- **コマンド形式**: 1行1コマンドの生テキスト（コマンドのみ）

---

## 2. 調整方針

### 2.1 A2A 入出力スキーマは変更しない（重要な前提）

本調整は **`src/agents/coding_agent.py` の `instruction`（プロンプト文字列）と、
それに対応するテストのみ**を変更対象とする。

- A2A のリクエスト/レスポンス スキーマは `src/schemas/a2a.py`
  （`A2ARequest` / `A2AResponse` / `A2AResponse.from_text`）に定義され、
  `src/routers/a2a.py` のみがこれを消費している。**この2ファイルは変更しない。**
- 出力ワイヤ形式（`result.artifacts[0].parts[0].text` に単一テキストを格納する構造）は不変。
- HTTP エンドポイント（`POST /`）・リクエスト JSON 形状・レスポンス JSON 形状も一切変更しない。
- 変わるのは `text` フィールドの**中身**（自然文の内容）のみであり、
  それを「spec 全文」「コマンド列」の2パターンに限定する。

つまり本調整は **CA の思考・応答スタイルの変更**であり、**RTG との通信インターフェースには
一切影響しない**。

### 2.2 判定の場所：LLM（instruction）で判定

RTG は A2A の**質問テキスト先頭パターン**で種別を伝えており、`metadata` に種別を示す
専用フィールドは無い。そのため判定は従来どおり LLM（Gemini）に委ね、
`coding_agent.py` の `instruction` のみを書き換える最小構成とする。
`src/routers/a2a.py` はリクエストの分類を行わず、従来どおり質問テキストをそのまま
`run_query` に渡す。

### 2.3 全リクエストを受理し、2形式へ強制マッピング

6 種すべてのリクエストを引き続き受理する（エラーにしない）。instruction で以下のとおり
**必ず 2 形式のいずれかへ強制マッピング**する。

| RTG メソッド | 調整後の出力形式 | 理由 |
|---|---|---|
| `create_spec` | **spec** | 要望からの計画立案そのもの |
| `edit_spec` | **spec** | 既存 spec の更新 |
| `generate_command_list` | **commands** | 実行コマンドの列挙要求 |
| `investigate_impact` | **spec** | 影響を実現方針/変更範囲/手順の枠で記述 |
| `notify_approval` | **commands** | 承認済みコマンドの模擬実行＝実行対象コマンド列を返す |
| `notify_rejection` | **spec** | コマンド列挙要求ではないため spec 側へ寄せる |
| `suggest_usecases` | **spec** | 変更候補を spec としてまとめて記述 |

判定基準（instruction に明文化する二分規則）:
- 「**実行すべきコマンドの列挙**」または「**承認されたコマンドの模擬実行**」を求める指示 → **commands**
- それ以外すべて（判定に迷う場合を含む） → **spec**

> **設計上の注記（既知のトレードオフ）**: `notify_rejection`（拒否通知への確認応答）や
> `suggest_usecases`（候補列挙）を spec 形式に寄せるのは、2形式への強制マッピングに伴う
> 割り切りであり、意味的にはやや不自然になり得る。まずは「コマンド列挙要求のみ commands、
> 他はすべて spec」というシンプルな二分規則を既定とし、運用実態に応じて上表のマッピングは
> 見直し可能とする。

### 2.4 やらないこと（対象外）

- `src/routers/a2a.py` / `src/schemas/a2a.py` / `src/services/gcs_client.py` /
  `src/agents/tools.py` の変更（ルーティング・ワイヤ形式・GCS 探索は不変）。
- RTG 本体側の改修（metadata による出力種別の明示指定などは本リポジトリの範囲外）。
- README「CA メソッド対応表」の改訂は任意（整合を取るなら工程3の後に追随更新してよい）。

---

## 3. 実装手順（工程順）

各工程の詳細は対応する detail-spec に収録。**この順で上から実施すれば実装〜検証まで完了する。**
工程は3つ（実装／テスト／検証）だが、それぞれ以下の Step 単位まで分解して進めること。

### 工程1: instruction 改修 — `src/agents/coding_agent.py`（改修）

詳細: [detail-spec/01](detail-spec/01-coding-agent-instruction.md)

| Step | 内容 |
|---|---|
| 1-1 | 着手前に `src/agents/coding_agent.py` を Read し、[detail-spec/01 §3 の Before 節](detail-spec/01-coding-agent-instruction.md#3-現状before指定部分の全文)と実ソースに差異がないか確認する |
| 1-2 | `instruction` のインライン文字列を、`_agent` 定義より前に置くモジュールレベル定数 `_INSTRUCTION` へ抽出する |
| 1-3 | `_INSTRUCTION` を2出力形式ポリシーへ書き換える：「## 探索方針」は維持／旧「## 回答スタイル（指示種別ごと）」6項目は削除／形式A(spec)・形式B(commands)を定義／「形式の選び方」（二分判定基準、迷ったら形式A）を追加／末尾の「コードブロックで全体を囲まない」指示は維持（[detail-spec/01 §4](detail-spec/01-coding-agent-instruction.md#4-変更後after指定後の全文)参照） |
| 1-4 | `_agent(instruction=_INSTRUCTION)` へ差し替える。`description` を実態に合わせて更新する（任意） |
| 1-5 | `python -c "from src.agents.coding_agent import _INSTRUCTION"` で import 単体確認（`google.*` 未インストール環境ではスタブ方式を使う） |
| 1-6 | `git diff` を見て、instruction/description 以外（`_agent`/`_runner`/`run_query` のロジック・A2Aスキーマ関連ファイル）に差分が無いことを確認する |

### 工程2: テスト実装 — `tests/`

詳細: [detail-spec/02 §1](detail-spec/02-tests-and-verification.md#1-テスト実装)

| Step | 内容 |
|---|---|
| 2-1 | `tests/test_instruction.py` を新規作成する。`google.*` の事前スタブ（`tests/test_a2a.py` と同一パターン）を行い、`_INSTRUCTION` の静的検証テスト5ケース（2形式定義・探索方針維持・コードフェンス禁止維持・旧6スタイル文言の不在・形式選択ルールの存在）を実装する |
| 2-2 | `tests/test_a2a.py` の `test_a2a_notify_rejection` / `test_a2a_suggest_usecases` の docstring を軽微更新する（任意。動作上の改修は不要） |

### 工程3: 検証（実行のみ・コード変更なし）

詳細: [detail-spec/02 §2](detail-spec/02-tests-and-verification.md#2-検証手順)

| Step | レベル | 内容 | docker |
|---|---|---|---|
| 3-1 | レベル1 | `pytest tests/ -v` を実行し全緑を確認する | 不要 |
| 3-2 | レベル2 | `uvicorn src.main:app --reload --port 8001` を起動し、6パターン（create_spec / edit_spec / generate_command_list / investigate_impact / notify_approval / notify_rejection / suggest_usecases の各質問文パターン）を curl で送信、応答 `text` が spec全文 または コマンド列のいずれか一方のみであることを目視確認する | **不要（docker未導入者向けの主たる代替検証）** |
| 3-3 | レベル3 | `docker build --platform linux/amd64` → `docker run`（ADC を volume mount）で同様に curl 確認する | 要（docker利用者向け・任意） |

> **依存関係**: 工程1（instruction 定数化）が完了していないと、工程2の静的検証テストが
> `_INSTRUCTION` を import できない。必ず **1 → 2 → 3**（各工程内も Step の番号順）に進めること。
> 逆順・並行作業は避ける。

---

## 4. 参照ファイル一覧

### 変更対象

| ファイル | 変更種別 | 対応工程 |
|---|---|---|
| `src/agents/coding_agent.py` | 改修（instruction を定数化＋2形式ポリシー化。`run_query`/`_agent`/`_runner` 等のロジックは不変） | 1 |
| `tests/test_instruction.py` | 新規（`_INSTRUCTION` の静的内容検証） | 2 |
| `tests/test_a2a.py` | 改修（軽微。RTGメソッド別モックの docstring・アサーション文言の見直し程度） | 2 |

### 参照のみ（変更しない・挙動確認用）

| ファイル | 確認内容 |
|---|---|
| `src/routers/a2a.py` | 全リクエストを分類せず受理し `run_query` へ委譲する現行動作の確認。**変更しない** |
| `src/schemas/a2a.py` | 出力ワイヤ形式 `A2AResponse.from_text`（単一テキスト格納）の確認。**変更しない** |
| `src/agents/tools.py` | GCS 探索ツール（`list_project_files`/`read_project_file`/`search_project_code`）。挙動不変 |
| `src/services/gcs_client.py` | GCS 読み取りプリミティブ。挙動不変 |
| `README.md` | 「CA メソッド対応表」（旧6種前提の記述。任意で追随更新） |

---

## 5. 完了条件（全体）

- [ ] `src/agents/coding_agent.py` の `instruction` が `_INSTRUCTION` 定数化され、
      2 形式（spec / commands）のみを定義し、旧6スタイル記述（影響調査報告文・
      模擬実行結果報告・拒否確認文・ユースケース候補列挙 等の個別スタイル）が削除されている。
      「## 探索方針」セクションと「コードブロック（```）で全体を囲まない」指示は維持する。
- [ ] `src/routers/a2a.py` と `src/schemas/a2a.py` に**差分が無い**（A2A 入出力スキーマ不変の確認）。
- [ ] `pytest tests/ -v` が全緑（新規 `test_instruction.py` を含む）。
- [ ] レベル2（ローカル起動）で6パターンの `message/send` を送信し、応答 `text` が
      **spec 全文 または コマンド列のいずれか一方のみ**であることを確認できる
      （影響調査報告文・模擬実行報告・拒否確認文・候補列挙が返らないこと）。
- [ ] docker 未導入者でも、レベル1・レベル2のみで検証を完了できる（レベル3は docker 利用者向けの追加確認）。
