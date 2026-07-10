"""
In/Out 事例集 検証ハーネス（実 Vertex AI 呼び出し）。

spec: spec/output-spec-or-commands/inout-casebook-verification-spec.md

10 パターンのプロンプトを実際に `run_query()` へ投げ、Vertex AI (Gemini) からの
実出力全文を `.steering/output-spec-or-commands/cases/<case_id>.md` に書き出す。
バグ探しではなく、現状実装の実出力をカタログ化することが目的（characterization）。

注意:
- `google.*` のスタブ化は行わない（実際に Vertex AI を呼ぶことが目的のため）。
  venv に `google-adk` / `google-genai` が導入済み、かつ ADC 認証済みであることが前提。
- 実行は `-m e2e` で選択的に走らせる（既定の `pytest tests/` では走らない）。
- 429 (RESOURCE_EXHAUSTED) 等の環境要因エラーは skip とし、アプリ側バグと誤判定しない。
"""
import asyncio
import re
from datetime import datetime
from pathlib import Path

import pytest

from src.agents.coding_agent import run_query

pytestmark = pytest.mark.e2e

_CASES_DIR = (
    Path(__file__).resolve().parent.parent
    / ".steering"
    / "output-spec-or-commands"
    / "cases"
)

# ---------------------------------------------------------------------------
# 入力プロンプト集
# spec §2.1/§2.2 のプロンプト全文と一致させること。
# ---------------------------------------------------------------------------

_EDIT_SPEC_1 = """\
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
"""

_EDIT_SPEC_2 = """\
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
"""

_GENERATE_COMMAND_LIST_1 = """\
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
"""

_GENERATE_COMMAND_LIST_2 = """\
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
"""

# (case_id, method, prompt, expected_format)
CASES = [
    (
        "create_spec-1",
        "create_spec",
        "以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\n"
        "カート画面にクーポン機能を追加したい",
        "spec",
    ),
    (
        "create_spec-2",
        "create_spec",
        "以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\n"
        "商品一覧画面にカテゴリ絞り込み検索を追加したい",
        "spec",
    ),
    ("edit_spec-1", "edit_spec", _EDIT_SPEC_1, "spec"),
    ("edit_spec-2", "edit_spec", _EDIT_SPEC_2, "spec"),
    (
        "generate_command_list-1",
        "generate_command_list",
        _GENERATE_COMMAND_LIST_1,
        "commands",
    ),
    (
        "generate_command_list-2",
        "generate_command_list",
        _GENERATE_COMMAND_LIST_2,
        "commands",
    ),
    (
        "investigate_impact-1",
        "investigate_impact",
        "以下のコマンドが対象システムに与える影響を、実現方針/変更範囲/手順の枠組みで報告してください。\n"
        "--- コマンド ---\nALTER TABLE orders ADD COLUMN coupon_id INTEGER;",
        "spec",
    ),
    (
        "notify_approval-1",
        "notify_approval",
        "以下のコマンドが承認されました。模擬実行し、実行したコマンドの一覧を報告してください。\n"
        "--- コマンド ---\ngit checkout -b feature/coupon\ntouch coupon_service.py\n"
        "pytest tests/test_coupon_service.py -v",
        "commands",
    ),
    (
        "notify_rejection-1",
        "notify_rejection",
        "以下のコマンドは拒否されました。実行しないでください。\n"
        "--- コマンド ---\ngit push --force origin main",
        "spec",
    ),
    (
        "suggest_usecases-1",
        "suggest_usecases",
        "以下の対象ソースを分析し、ユーザーが「変更したいこと」の候補を2〜3件、1行1件で列挙してください。\n"
        "--- 対象ソース ---\n"
        "（対象アプリ未指定。一般的なECサイトのカート機能を前提に候補を提示してください）",
        "spec",
    ),
]

_SPEC_HEADINGS = ("## 実現方針", "## 変更範囲", "## 手順")
_TOOL_NAME_LEAK_PATTERNS = (
    "list_project_files(",
    "read_project_file(",
    "search_project_code(",
)
_REFUSAL_PHRASES = (
    "実行権限がない",
    "機能範囲外",
    "実行することはできません",
    "私の能力は",
)


def classify_output(text: str) -> tuple[str, str | None]:
    """
    出力テキストを "spec" / "commands" / "other" のいずれかに分類する。
    "other" の場合、第2要素にサブラベル（tool-name-leak / spec-refusal / unclassified）を返す。
    spec §3 の分類ルールに対応する実装。
    """
    heading_hits = sum(1 for h in _SPEC_HEADINGS if h in text)
    has_tool_leak = any(p in text for p in _TOOL_NAME_LEAK_PATTERNS)

    if heading_hits >= 2:
        return "spec", None

    if not has_tool_leak:
        # spec 見出しが無く、ツール名リークも無い → commands とみなす
        # (見出しが0〜1個のケースは commands 側として扱う。0件かつツール名リークがあれば other 側で捕捉)
        if heading_hits == 0:
            return "commands", None

    if has_tool_leak:
        return "other", "tool-name-leak"

    if any(p in text for p in _REFUSAL_PHRASES):
        return "other", "spec-refusal"

    return "other", "unclassified"


def _write_case_file(
    case_id: str,
    method: str,
    prompt: str,
    expected_format: str,
    output_text: str,
    actual_format: str,
    sub_label: str | None,
) -> None:
    _CASES_DIR.mkdir(parents=True, exist_ok=True)
    matched = actual_format == expected_format
    lines = [
        f"# {case_id}",
        "",
        f"- **メソッド**: {method}",
        f"- **期待形式**: {expected_format}",
        f"- **実出力分類**: {actual_format}",
        f"- **サブラベル**: {sub_label or '(該当なし)'}",
        f"- **一致**: {matched}",
        f"- **記録日時**: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## 入力プロンプト",
        "",
        prompt,
        "",
        "## 出力全文",
        "",
        output_text,
        "",
    ]
    (_CASES_DIR / f"{case_id}.md").write_text("\n".join(lines), encoding="utf-8")


@pytest.mark.parametrize("case_id, method, prompt, expected_format", CASES, ids=[c[0] for c in CASES])
def test_inout_case(case_id, method, prompt, expected_format):
    """指定プロンプトを実 Vertex AI に投げ、出力を分類・記録する。2形式不変条件のみ hard assert。"""
    try:
        output_text = asyncio.run(run_query(prompt, project_id=None))
    except Exception as exc:  # noqa: BLE001 — 環境要因エラーの判定に例外種別を問わず文字列を見る
        message = str(exc)
        if "RESOURCE_EXHAUSTED" in message or "429" in message:
            pytest.skip(f"{case_id}: レート制限のためskip（環境要因、アプリバグではない）: {message}")
        raise

    actual_format, sub_label = classify_output(output_text)
    _write_case_file(case_id, method, prompt, expected_format, output_text, actual_format, sub_label)

    # 主基準（spec §5.1）: 2形式不変条件のみ hard assert。期待マッピングとの一致(§5.2)は
    # 事例集レポート側で observational に記録する（本テストでは failしない）。
    assert actual_format in ("spec", "commands"), (
        f"{case_id}: 2形式のいずれにも分類されない出力 (sub_label={sub_label}):\n{output_text}"
    )
