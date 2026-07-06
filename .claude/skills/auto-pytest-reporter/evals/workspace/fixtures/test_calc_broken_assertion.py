"""
フィクスチャ: 【eval-self-heal 用】テストコード側に意図的な誤り（誤アサーション）を仕込んだバージョン。
- test_add_positive: 期待値が間違い（5 ではなく 99）
- test_divide_normal: 期待値が間違い（5.0 ではなく 9.9）
これらはテストコードのミスであり、target_calc.py は正しい。
Claude がテストコードのアサーションを修正することで PASS になる想定。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from target_calc import add, multiply, divide
import pytest


def test_add_positive():
    # 修正: 2 + 3 = 5 が正しい期待値
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, -4) == -5


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide_normal():
    # 修正: 10.0 / 2.0 = 5.0 が正しい期待値
    assert divide(10.0, 2.0) == 5.0


def test_divide_by_zero():
    with pytest.raises(ValueError, match="ゼロ除算"):
        divide(5.0, 0.0)
