# 編集単位 1: src/agents/coding_agent.py（改修）

**依存**: なし（最初に着手する編集単位）
**上位ドキュメント**: [../output-spec-or-commands-spec.md](../output-spec-or-commands-spec.md)（工程1）

---

## 1. 対象ファイル / 変更種別

- ファイル: `src/agents/coding_agent.py`
- 種別: 改修（`LlmAgent` の `instruction` 文字列を書き換え。`_agent`/`_runner`/`run_query`
  の構造・シグネチャ・ロジックは変更しない）

## 2. 変更しないものの明示（A2A 非影響の確認）

- 本ファイルは `src/schemas/a2a.py` / `src/routers/a2a.py` を import していない。
  ここでの変更が A2A のリクエスト/レスポンス スキーマに影響することはない。
- `run_query(question: str, project_id: str | None = None) -> str` のシグネチャ・戻り値型は不変。
  戻り値は引き続き「収集したテキストを連結した単一文字列」であり、
  呼び出し元 `src/routers/a2a.py` の `A2AResponse.from_text(answer)` への受け渡し方法も不変。
- `tools=[list_project_files, read_project_file, search_project_code]` の登録、
  `_LOCAL_TIMEOUT = 120.0`、GCS 探索フロー（[spec/coding-agent/adk-tools-spec.md](../../coding-agent/adk-tools-spec.md) 参照）は変更しない。

## 3. 現状（Before）：`instruction` 部分の全文

2026-07-09 時点（`feature/output-spec-or-commands` ブランチ、`master` から分岐直後）の該当箇所:

```python
_agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="RTG の指示に従い spec 作成・コマンド生成・影響調査等を行うコーディングエージェント",
    instruction=(
        "あなたはシニアソフトウェアエンジニアです。"
        "受け取った指示の種別に応じた回答をテキストのみで返してください。\n\n"
        "## 探索方針\n"
        "対象アプリのコードに関わる指示（spec 作成・影響調査・ユースケース候補等）では、"
        "推測で回答せず、まず list_project_files で全体像を掴み、read_project_file / "
        "search_project_code で関連コードを確認してから回答すること。"
        "対象アプリが指定されていない（ツールが「指定されていない」旨を返す）場合は、"
        "ツールを使わず一般的な方針として回答すること。\n\n"
        "## 回答スタイル（指示種別ごと）\n"
        "- spec 作成・更新: Markdown 形式。"
        "## 実現方針 / ## 変更範囲 / ## 手順 の3セクション構成を推奨。\n"
        "- コマンドリスト生成: 1行1コマンド・コマンドのみ（説明・番号・コードフェンス不要）。\n"
        "- 影響調査: 影響範囲・関連コード名・変更箇所を含めた簡潔な日本語報告文。\n"
        "- 模擬実行結果: 実際のシステムには変更を加えない前提で結果を日本語で報告。\n"
        "- 拒否通知: 「了解しました。実行しません。」等の簡潔な確認文。\n"
        "- ユースケース候補: 「〜したい」形式で1行1件、2〜3件列挙。\n"
        "コードブロック（```）で全体を囲まないこと。"
    ),
    tools=[list_project_files, read_project_file, search_project_code],
)
```

> **着手前の再確認**: 別セッションでこの編集単位に着手する場合、
> `src/agents/coding_agent.py` を一度 Read し、上記 Before 節と実際のソースに
> 食い違いがないか確認すること（食い違いがあれば、それを踏まえて次節の After を適用し直す）。

## 4. 変更後（After）：`instruction` 部分の全文

`instruction` をインライン文字列からモジュールレベル定数 `_INSTRUCTION` へ抽出し、
2 出力形式ポリシーへ書き換える。定数化する理由は工程2で `tests/test_instruction.py` から
`_INSTRUCTION` を直接 import して静的検証できるようにするため。

```python
_INSTRUCTION = (
    "あなたはシニアソフトウェアエンジニアです。"
    "受け取った指示がどのような種別であっても、回答は必ず次の2形式のうち"
    "いずれか一方のみで返してください。それ以外の形式（説明文・確認応答・箇条書きの候補列挙等）"
    "では絶対に回答しないこと。\n\n"
    "## 探索方針\n"
    "対象アプリのコードに関わる指示では、推測で回答せず、まず list_project_files で"
    "全体像を掴み、read_project_file / search_project_code で関連コードを確認してから"
    "回答すること。対象アプリが指定されていない（ツールが「指定されていない」旨を返す）"
    "場合は、ツールを使わず一般的な方針として回答すること。\n\n"
    "## 出力形式（必ずこの2つのいずれか一方）\n"
    "### 形式A: spec\n"
    "Markdown 形式。## 実現方針 / ## 変更範囲 / ## 手順 の3セクション構成。\n"
    "### 形式B: commands\n"
    "1行1コマンド・コマンドのみ（説明・番号・コードフェンス不要）。\n\n"
    "## 形式の選び方\n"
    "受け取った指示が「実行すべきコマンドの列挙」または「承認されたコマンドの模擬実行」を"
    "求めるものである場合は形式B(commands)を返すこと。それ以外の指示（spec作成・編集の依頼、"
    "影響調査、拒否通知への応答、ユースケース候補の提示など）はすべて形式A(spec)で返すこと。"
    "判断に迷う場合は形式A(spec)を選ぶこと。\n\n"
    "コードブロック（```）で全体を囲まないこと。"
)

_agent = LlmAgent(
    name="coding_agent",
    model=GEMINI_MODEL,
    description="RTG の指示に従い、spec 全文またはコマンド列のいずれかを生成するコーディングエージェント",
    instruction=_INSTRUCTION,
    tools=[list_project_files, read_project_file, search_project_code],
)
```

## 5. 差分の要点

- **追加**: モジュールレベル定数 `_INSTRUCTION`（`_agent` 定義より前に配置）。
- **変更**: `_agent` の `instruction=` 引数を、インライン文字列 → `_INSTRUCTION` 参照に変更。
- **変更**: `_agent` の `description` を「spec 作成・コマンド生成・影響調査等を行う」→
  「spec 全文またはコマンド列のいずれかを生成する」に更新（実態に合わせる。任意だが推奨）。
- **維持**: 「## 探索方針」セクションの文面（GCS 探索ツールの使い方指示）はそのまま維持。
- **維持**: 末尾の「コードブロック（```）で全体を囲まないこと」指示はそのまま維持。
- **削除**: 「## 回答スタイル（指示種別ごと）」の6項目列挙（spec作成・更新／コマンドリスト生成／
  影響調査／模擬実行結果／拒否通知／ユースケース候補）。
- **新設**: 「## 出力形式（必ずこの2つのいずれか一方）」（形式A=spec／形式B=commands の定義）と
  「## 形式の選び方」（二分判定基準。迷ったら形式A）。
- **変更なし**: `_APP_NAME` / `_LOCAL_TIMEOUT` / `_session_svc` / `tools=[...]` / `_runner` /
  `run_query` の実装。

## 6. 理由・設計意図

- instruction を定数化するのは、工程2のテストが「LLM を実際に呼ばずに instruction の
  内容（2形式ポリシーを含み、旧6スタイル語を含まないこと）を静的に検証する」ため。
  ADK/Vertex AI をモックしても instruction 文字列自体は変わらないので、文字列检查は
  低コストかつ確実な回帰防止になる。
- 「判断に迷う場合は形式A(spec)を選ぶこと」を明記したのは、6メソッド中4つ
  （create_spec/edit_spec/investigate_impact/notify_rejection/suggest_usecases）を
  spec に寄せる設計方針（[概要 spec §2.3](../output-spec-or-commands-spec.md#23-全リクエストを受理し2形式へ強制マッピング)）を
  LLM が安定して再現できるようにするため。commands 形式はコマンド列挙・模擬実行の
  2メソッドのみに限定する狭い条件とし、それ以外を広く spec の受け皿にする。
- 「絶対に回答しないこと」という強い禁止表現を先頭に置いたのは、Gemini が指示種別ごとに
  細かく口調を変える既存の癖（影響調査報告文・確認応答文など）を上書きするため。

## 7. 注意点・エッジケース

- instruction 文字列の日本語表現（句読点の使い方、体言止めの有無等）は既存コードの
  スタイルに合わせ、不要な文体変更をしないこと。
- `_INSTRUCTION` は `f-string` にしない（動的な値を埋め込まないため通常の文字列リテラルでよい）。
- `description` の変更は完了条件に含めていない（任意）。変更する場合、既存テストの
  文言 assert が `description` を参照していないことを確認する（本 repo のテストは
  `description` を検証していない。[detail-spec/02](02-tests-and-verification.md) 参照）。

## 8. この編集単位の完了条件

- [ ] `_INSTRUCTION` 定数が新設され、`_agent(instruction=...)` がこれを参照している。
- [ ] `_INSTRUCTION` に「形式A」「形式B」（または同等の spec/commands 呼称）の定義と、
      形式選択の二分判定基準が含まれている。
- [ ] 「## 探索方針」の文面と「コードブロックで全体を囲まない」指示が維持されている。
- [ ] 旧「## 回答スタイル（指示種別ごと）」の6項目列挙が削除されている。
- [ ] `python -c "from src.agents.coding_agent import _INSTRUCTION; print(len(_INSTRUCTION))"`
      が例外なく通る（`google.*` 未インストール環境では [detail-spec/02](02-tests-and-verification.md)
      のスタブ方式を用いること）。
- [ ] `_agent` / `_runner` / `run_query` の関数シグネチャ・ロジックに変更がない
      （`git diff` で instruction/description 以外の差分が無いことを確認）。

## 9. 依存

- なし。最初に着手してよい。
