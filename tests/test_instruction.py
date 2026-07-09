"""
coding_agent._INSTRUCTION の静的内容検証。
LLM を実際に呼ばず、instruction 文字列が2出力形式ポリシー
（spec 全文 / コマンド列のいずれか一方のみ）へ書き換わっていることを確認する。
"""
import sys
from unittest.mock import MagicMock

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
