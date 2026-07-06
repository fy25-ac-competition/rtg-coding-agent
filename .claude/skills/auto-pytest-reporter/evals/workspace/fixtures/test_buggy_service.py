"""
フィクスチャ: 【eval-app-bug 用】アプリ側バグを検出する正しいテストコード。
target_buggy_service.py にバグがあるため、このテストは正しく書かれていても FAIL する。
Claude はこのファイルを修正してはいけない（修正してもバグは直らない）。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from target_buggy_service import discount, apply_tax


def test_discount_10_percent():
    """1000円の商品を10%引きにすると900円になるべき"""
    result = discount(1000.0, 0.1)
    assert result == 900.0, f"期待値 900.0、実際 {result}"


def test_discount_zero():
    """割引率0%なら価格変わらず"""
    assert discount(500.0, 0.0) == 500.0


def test_apply_tax_10_percent():
    """1000円に消費税10%で1100円になるべき"""
    result = apply_tax(1000.0, 0.1)
    assert result == 1100.0, f"期待値 1100.0、実際 {result}"
