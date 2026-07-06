"""
フィクスチャ: テスト対象モジュール（正常に動作する計算ライブラリ）
eval-success と eval-self-heal で使用。
"""


def add(a: int, b: int) -> int:
    return a + b


def multiply(a: int, b: int) -> int:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("ゼロ除算は禁止されています")
    return a / b
