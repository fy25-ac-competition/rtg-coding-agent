"""
フィクスチャ: 【eval-success 用】最初から正しいテストコード。
このテストはそのまま実行すると全て PASS する。
target_calc.py と同ディレクトリで `python -m pytest test_calc_success.py -v` で実行。
"""
import sys
import os

# フィクスチャディレクトリを sys.path に追加
sys.path.insert(0, os.path.dirname(__file__))

from target_calc import add, multiply, divide
import pytest


def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, -4) == -5


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide_normal():
    assert divide(10.0, 2.0) == 5.0


def test_divide_by_zero():
    with pytest.raises(ValueError, match="ゼロ除算"):
        divide(5.0, 0.0)
