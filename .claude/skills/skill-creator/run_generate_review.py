"""UTF-8 エンコード対応で generate_review を実行するラッパー"""
import builtins
import pathlib
import sys

# builtins.open を UTF-8 デフォルトにパッチ
orig_open = builtins.open
def patched_open(file, mode='r', **kwargs):
    if isinstance(mode, str) and 'b' not in mode and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
    return orig_open(file, mode, **kwargs)
builtins.open = patched_open

# pathlib.Path.read_text を UTF-8 デフォルトにパッチ
orig_read_text = pathlib.Path.read_text
def patched_read_text(self, encoding=None, errors=None):
    return orig_read_text(self, encoding=encoding or 'utf-8', errors=errors)
pathlib.Path.read_text = patched_read_text

# pathlib.Path.write_text を UTF-8 デフォルトにパッチ
orig_write_text = pathlib.Path.write_text
def patched_write_text(self, data, encoding=None, errors=None, newline=None):
    return orig_write_text(self, data, encoding=encoding or 'utf-8', errors=errors, newline=newline)
pathlib.Path.write_text = patched_write_text

# generate_review の main を呼ぶ
sys.path.insert(0, str(pathlib.Path(__file__).parent / "eval-viewer"))
from generate_review import main
main()
