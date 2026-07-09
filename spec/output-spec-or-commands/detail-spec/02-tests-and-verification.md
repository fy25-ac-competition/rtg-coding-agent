# 編集単位 2: テスト実装 ＋ 検証（工程2・工程3）

**依存**: [01-coding-agent-instruction.md](01-coding-agent-instruction.md) 完了後
（`_INSTRUCTION` 定数が存在しないと本ファイルの静的検証テストが書けないため）
**上位ドキュメント**: [../output-spec-or-commands-spec.md](../output-spec-or-commands-spec.md)（工程2・工程3）

---

## 1. テスト実装

### 1.1 新規: `tests/test_instruction.py`

**目的**: LLM を実際に呼ばずに、`_INSTRUCTION` の**文面**が2形式ポリシーへ
書き換わっていることを静的に検証する（安価な回帰防止）。

既存 `tests/test_a2a.py` に倣い、`google.*` 未インストール環境でも import が通るよう
事前スタブを行う（[tests/test_a2a.py:13-18](../../../tests/test_a2a.py#L13-L18) と同じパターン）。

```python
"""
coding_agent._INSTRUCTION の静的内容検証。
LLM を実際に呼ばず、instruction 文字列が2出力形式ポリシー
（spec 全文 / コマンド列のいずれか一方のみ）へ書き換わっていることを確認する。
"""
import sys
from unittest.mock import MagicMock

import pytest

# google.* 未インストール環境でも import を通せるよう事前スタブ
# （tests/test_a2a.py と同一パターン）
for _mod in (
    "google", "google.adk", "google.adk.agents", "google.adk.runners",
    "google.adk.sessions", "google.adk.tools", "google.genai", "google.genai.types",
    "google.cloud", "google.cloud.storage",
):
    sys.modules.setdefault(_mod, MagicMock())

from src.agents.coding_agent import _INSTRUCTION  # noqa: E402


def test_instruction_defines_two_output_formats():
    """spec形式・commands形式の両方が定義されていること。"""
    assert "spec" in _INSTRUCTION.lower()
    assert "commands" in _INSTRUCTION.lower() or "コマンド" in _INSTRUCTION


def test_instruction_keeps_exploration_policy():
    """既存の GCS 探索方針（## 探索方針）が維持されていること。"""
    assert "探索方針" in _INSTRUCTION
    assert "list_project_files" in _INSTRUCTION


def test_instruction_keeps_no_code_fence_rule():
    """コードブロックで全体を囲まない指示が維持されていること。"""
    assert "コードブロック" in _INSTRUCTION
    assert "```" in _INSTRUCTION


def test_instruction_removes_legacy_multi_style_wording():
    """
    旧6スタイル個別記述（影響調査報告文・模擬実行結果・拒否通知の確認文・
    ユースケース候補列挙）の文言が残っていないこと。
    2形式ポリシーへの一本化が漏れなく行われたことを確認する。
    """
    legacy_phrases = [
        "影響範囲・関連コード名・変更箇所を含めた簡潔な日本語報告文",
        "実際のシステムには変更を加えない前提で結果を日本語で報告",
        "了解しました。実行しません。",
        "「〜したい」形式で1行1件",
    ]
    for phrase in legacy_phrases:
        assert phrase not in _INSTRUCTION, f"旧スタイル文言が残存: {phrase!r}"


def test_instruction_has_format_selection_rule():
    """形式の選び方（二分判定基準）が明記されていること。"""
    assert "形式" in _INSTRUCTION or "choose" in _INSTRUCTION.lower()
```

> 上記 `test_instruction_defines_two_output_formats` 等は文言の**存在確認**であり、
> [detail-spec/01 §4](01-coding-agent-instruction.md#4-変更後after指定後の全文) の After 案どおりに実装すれば
> そのまま通る想定。実装時に文言を調整した場合はテスト側の期待文字列も追随して直すこと
> （文言一致ではなく「ポリシーの骨子が残っているか」を検証する意図を優先する）。

### 1.2 改修: `tests/test_a2a.py`（軽微）

`tests/test_a2a.py` は `run_query` を **mock 化**して呼び出しており（例:
[tests/test_a2a.py:45](../../../tests/test_a2a.py#L45) `@patch("src.routers.a2a.run_query", ...)`）、
実際の instruction 文字列には依存していない。したがって **動作上の改修は不要**。

以下は整合性のための軽微な見直しのみ行う（コード的な意味は変えない）:

- [tests/test_a2a.py:102-114](../../../tests/test_a2a.py#L102-L114) `test_a2a_notify_rejection` と
  [tests/test_a2a.py:116-131](../../../tests/test_a2a.py#L116-L131) `test_a2a_suggest_usecases` の
  docstring を、「拒否通知リクエストが処理される」→「拒否通知リクエストが処理される
  （調整後は spec 形式のテキストが返る想定。ここでは mock 値をそのまま検証するのみ）」
  のように一言補足する（**任意**。テストの pass/fail には影響しない）。
- 新しいテストケースを追加する必要はない（形式の中身検証は `test_instruction.py` 側の責務）。

## 2. 検証手順

**docker をインストールしていない人を想定し、レベル1・レベル2のみで検証を完結できるようにする。**
レベル3は docker 利用者向けの追加確認であり必須ではない。

### レベル1: 単体テスト（誰でも・docker/GCP 不要）

```bash
cd rtg-coding-agent
source venv/bin/activate   # 未作成なら: python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install pytest httpx

pytest tests/ -v
```

- 期待結果: 全テスト green。特に `tests/test_instruction.py` の5ケースと
  `tests/test_a2a.py` の全ケースが通ること。
- `google.*` は各テストファイル内で事前スタブされているため、`google-adk` や
  GCP 認証が無い環境でも実行できる（[README.md](../../../README.md) 「テスト実行」節と同じ前提）。

### レベル2: ローカル起動での疎通確認（docker 不要・主たる代替検証手段）

**docker が無い場合はこのレベルを検証の中心とする。** Vertex AI への実アクセスが必要なため
GCP 認証（ADC）は要るが、docker は不要。

```bash
cd rtg-coding-agent
source venv/bin/activate
cp .env.example .env   # 未作成なら。GOOGLE_CLOUD_PROJECT 等を編集
gcloud auth application-default login   # 未認証なら

uvicorn src.main:app --reload --port 8001
```

別ターミナルから、6メソッドそれぞれに対応する質問文で `message/send` を送信し、
応答 `result.artifacts[0].parts[0].text` が **spec全文 または コマンド列のいずれか一方のみ**
であることを目視確認する（[README.md](../../../README.md) 「A2A ワイヤ形式リファレンス」の
リクエスト形状に準拠）。

```bash
# 例1: create_spec → spec 形式が期待値
curl -s -X POST http://localhost:8001/ -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1, "method": "message/send",
  "params": {"message": {"role": "user", "parts": [
    {"text": "以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\nカート画面にクーポン機能を追加したい"}
  ]}}
}' | python -m json.tool

# 例2: generate_command_list → commands 形式が期待値
curl -s -X POST http://localhost:8001/ -H "Content-Type: application/json" -d '{
  "jsonrpc": "2.0", "id": 1, "method": "message/send",
  "params": {"message": {"role": "user", "parts": [
    {"text": "以下の spec を実現するために実行すべきコマンドを、実行順に列挙してください。\n--- spec ---\n# spec: クーポン機能\n..."}
  ]}}
}' | python -m json.tool

# 例3〜6: investigate_impact / notify_approval / notify_rejection / suggest_usecases も
# README.md「CA メソッド対応表」の質問テキスト先頭パターンに沿って同様に送信し、
# 例3(investigate_impact)・例5(notify_rejection)・例6(suggest_usecases) は spec 形式、
# 例4(notify_approval) は commands 形式が返ることを確認する。
```

確認observ観点:
- 応答テキストが Markdown spec（`## 実現方針` 等の見出しを含む）か、
  1行1コマンドの生テキストかのいずれかであること。
- 「了解しました。実行しません。」のような確認応答文、「〜したい」の箇条書き候補、
  自由形式の報告文が**返らない**こと（返った場合は工程1の instruction 見直しが必要）。

### レベル3: docker での疎通確認（docker 利用者向け・任意）

docker が導入済みの環境向けの追加確認。Cloud Run 本番相当のイメージで動作確認したい場合に行う。
**docker が無い場合は本レベルを省略し、レベル1・レベル2の結果をもって検証完了としてよい。**

```bash
cd rtg-coding-agent
docker build --platform linux/amd64 -t rtg-coding-agent:local .

docker run --rm -p 8001:8080 \
  -e GOOGLE_GENAI_USE_VERTEXAI=1 \
  -e GOOGLE_CLOUD_PROJECT=<your-project-id> \
  -e GOOGLE_CLOUD_LOCATION=us-central1 \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  rtg-coding-agent:local
```

- ADC 認証情報を `-v` でコンテナに読み取り専用マウントすることで、
  コンテナ内からも `gcloud auth application-default login` 済みの認証情報を使える。
- 起動後、レベル2と同じ curl コマンド（ポートは `8001`）で疎通確認する。

## 3. この編集単位の完了条件

- [ ] `tests/test_instruction.py` が新規作成され、上記5テストケース相当が実装されている。
- [ ] `pytest tests/ -v` が全緑。
- [ ] レベル1（単体テスト）がパスすることを確認済み。
- [ ] レベル2（ローカル起動＋curl）で6パターンいずれも spec/commands の
      いずれか一方のみが返ることを確認済み（docker 未導入者はここまでで検証完了とする）。
- [ ] （docker 導入済みの場合のみ）レベル3で同様の確認が取れている。

## 4. 依存

- [01-coding-agent-instruction.md](01-coding-agent-instruction.md) — `_INSTRUCTION` 定数が
  実装済みであることが前提。
