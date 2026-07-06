"""UTF-8 エンコード対応で aggregate_benchmark を実行するラッパー"""
import builtins
import sys

orig_open = builtins.open

def patched_open(file, mode='r', **kwargs):
    if isinstance(mode, str) and 'b' not in mode and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
    return orig_open(file, mode, **kwargs)

builtins.open = patched_open

sys.argv = ['aggregate_benchmark', sys.argv[1], '--skill-name', sys.argv[2]]
from scripts.aggregate_benchmark import main
main()
