# 編集単位 1: src/services/gcs_client.py（改修）

**依存**: なし（最初に着手する編集単位）
**このファイルを読むだけで着手できる**: 実装対象コードは本ファイル内に完全収録している。

---

## 1. 対象ファイル / 変更種別

- ファイル: `src/services/gcs_client.py`
- 種別: 改修（既存の一括ロード関数を削除し、探索プリミティブ 3 種を新設）

## 2. 現状（Before）

2026-07-06 時点の全文（29行のモジュール docstring 部分は省略せず記載）:

```python
"""
Google Cloud Storage からソースコードを読み込む。

バケット構造:
  gs://<GCS_BUCKET>/<project_id>/<ファイルパス>

対象アプリ識別子（demo:<name>）から自動的に project_id を解決する:
  demo:system-m  →  gs://<GCS_BUCKET>/system-m/...
  demo:system-s  →  gs://<GCS_BUCKET>/system-s/...
"""
import logging

from google.cloud import storage
from src.config import GCS_BUCKET

logger = logging.getLogger(__name__)

_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".whl", ".pyc", ".pyo",
    ".map", ".lock",
}
_MAX_FILE_BYTES = 50_000     # 1 ファイルあたり最大 50 KB
_MAX_TOTAL_BYTES = 300_000   # コード文脈全体の最大 300 KB


def load_project_context(project_id: str) -> str:
    """
    GCS の <project_id>/ プレフィックス以下のファイルを読み込み、
    LLM に渡すコード文脈文字列を組み立てて返す。
    """
    if not GCS_BUCKET:
        return ""

    client = storage.Client()
    prefix = f"{project_id}/"
    blobs = sorted(client.list_blobs(GCS_BUCKET, prefix=prefix), key=lambda b: b.name)

    parts: list[str] = []
    total = 0

    for blob in blobs:
        relative_path = blob.name[len(prefix):]
        if not relative_path:
            continue

        suffix = "." + relative_path.rsplit(".", 1)[-1].lower() if "." in relative_path else ""
        if suffix in _SKIP_EXTENSIONS:
            continue
        if blob.size > _MAX_FILE_BYTES or total + blob.size > _MAX_TOTAL_BYTES:
            continue

        try:
            content = blob.download_as_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        parts.append(f"### {relative_path}\n```\n{content}\n```")
        total += blob.size

    return "\n\n".join(parts)


def load_project_context_for_source(source: str | None) -> str:
    """
    target_source 識別子から GCS のコード文脈を読み込む。

    対応形式:
      demo:<name>   →  gs://<GCS_BUCKET>/<name>/ 以下を読み込む
      github:<url>  →  GCS への事前アップロードが必要なため現状はスキップ
      その他 / None →  空文字を返す
    """
    if not source or not GCS_BUCKET:
        return ""

    if source.startswith("demo:"):
        project_id = source[len("demo:"):]
    else:
        return ""

    try:
        context = load_project_context(project_id)
        if context:
            logger.debug("GCS から %s のコード文脈を取得しました", source)
        return context
    except Exception as exc:
        logger.warning("GCS からのコード文脈取得に失敗しました (source=%s): %s", source, exc)
        return ""
```

乖離チェック済み（[00-overview.md §4](00-overview.md#4-乖離チェック結果実ソース-vs-本-spec2026-07-06-時点)）。

## 3. 変更後（After）：完全なファイル全文

```python
"""
Google Cloud Storage 上のソースコードを探索するためのプリミティブ関数群。

バケット構造:
  gs://<GCS_BUCKET>/<project_id>/<ファイルパス>

以前はここでプロジェクト全体を一括ダンプして LLM プロンプトへ注入していたが、
ADK LlmAgent 側にツール（list_files / read_file / search_code をラップした
FunctionTool、src/agents/tools.py 参照）を持たせ、LLM が必要なファイルだけを
自律的に探索する方式へ移行した。一括ダンプ用の関数は本ファイルから削除済み。

対象アプリ識別子（demo:<name>）から自動的に project_id を解決する:
  demo:system-m  →  gs://<GCS_BUCKET>/system-m/...
  demo:system-s  →  gs://<GCS_BUCKET>/system-s/...
"""
import re

from google.cloud import storage
from src.config import GCS_BUCKET

_SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".whl", ".pyc", ".pyo",
    ".map", ".lock",
}
_MAX_FILE_BYTES = 50_000       # 1 ファイルあたり最大 50 KB（read_file / search_code で適用）
_MAX_TOTAL_BYTES = 300_000     # 未使用（旧一括ダンプ用の定数だが後方互換のため残置）
_MAX_SEARCH_HITS = 100         # search_code が返すマッチ行の最大件数


def _skip_suffix(relative_path: str) -> bool:
    """スキップ対象拡張子（バイナリ・生成物）なら True。"""
    suffix = "." + relative_path.rsplit(".", 1)[-1].lower() if "." in relative_path else ""
    return suffix in _SKIP_EXTENSIONS


def list_files(project_id: str) -> list[str]:
    """
    <project_id>/ プレフィックス配下のファイル相対パス一覧を返す。
    スキップ拡張子（バイナリ・生成物）は除外する。GCS_BUCKET 未設定時は空リスト。
    """
    if not GCS_BUCKET:
        return []

    client = storage.Client()
    prefix = f"{project_id}/"
    result: list[str] = []
    for blob in sorted(client.list_blobs(GCS_BUCKET, prefix=prefix), key=lambda b: b.name):
        rel = blob.name[len(prefix):]
        if not rel or _skip_suffix(rel):
            continue
        result.append(rel)
    return result


def read_file(project_id: str, path: str) -> str:
    """
    <project_id>/<path> のファイル内容（UTF-8）を返す。
    存在しない/サイズ上限超/取得失敗時は、例外を投げず
    エラー内容を示す文字列を返す（LLM ツール応答として自然に扱えるようにするため）。
    """
    if not GCS_BUCKET:
        return "[エラー] GCS_BUCKET が未設定です。"

    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(f"{project_id}/{path}")
    if not blob.exists():
        return f"[エラー] ファイルが見つかりません: {path}"

    blob.reload()  # list_blobs 経由でないため size 等のメタデータを明示的に取得する
    if blob.size and blob.size > _MAX_FILE_BYTES:
        return f"[エラー] ファイルが大きすぎます（{blob.size} bytes > {_MAX_FILE_BYTES}）: {path}"

    try:
        return blob.download_as_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - 個別ファイルの取得失敗で全体を落とさない
        return f"[エラー] 読み込みに失敗しました: {path} ({exc})"


def search_code(project_id: str, pattern: str) -> list[str]:
    """
    <project_id>/ 配下のテキストファイルを正規表現 pattern で横断検索し、
    マッチ行を "<相対パス>:<行番号>: <行内容>" 形式で返す（最大 _MAX_SEARCH_HITS 件）。
    バイナリ・サイズ上限超のファイルはスキップする。pattern が不正な正規表現の場合は
    例外を投げずエラー文字列 1 件のリストを返す。
    """
    if not GCS_BUCKET:
        return ["[エラー] GCS_BUCKET が未設定です。"]
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return [f"[エラー] 正規表現が不正です: {exc}"]

    client = storage.Client()
    prefix = f"{project_id}/"
    hits: list[str] = []
    for blob in sorted(client.list_blobs(GCS_BUCKET, prefix=prefix), key=lambda b: b.name):
        rel = blob.name[len(prefix):]
        if not rel or _skip_suffix(rel):
            continue
        if blob.size and blob.size > _MAX_FILE_BYTES:
            continue
        try:
            text = blob.download_as_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - 個別ファイルの取得失敗はスキップして続行
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{rel}:{lineno}: {line.strip()}")
                if len(hits) >= _MAX_SEARCH_HITS:
                    return hits
    return hits
```

## 4. 差分の要点

- **削除**: `load_project_context(project_id)`、`load_project_context_for_source(source)`。
  呼び出し元は `src/routers/a2a.py` のみ（[04-a2a-router.md](04-a2a-router.md) で対応）。
- **削除**: `import logging` と `logger` 定義（一括ロード関数の警告ログでのみ使用していたため不要に。
  新プリミティブは例外を握りつぶさずエラー文字列として返す方針のためロギング不要）。
- **追加**: `import re`（`search_code` の正規表現コンパイルに使用）。
- **追加**: `_skip_suffix()` ヘルパー（`list_files`/`search_code` で共有）。
- **追加**: `_MAX_SEARCH_HITS = 100`。
- **追加**: `list_files` / `read_file` / `search_code` の 3 公開関数。
- **維持**: `_SKIP_EXTENSIONS`, `_MAX_FILE_BYTES` はそのまま流用。
- **維持（未使用のまま残置）**: `_MAX_TOTAL_BYTES` — 一括ダンプ廃止により本来不要だが、
  他モジュールから参照されていないか用心し定数自体は残す（実装時に grep で未参照を確認し、
  完全に不要と判断できれば削除しても構わない。判断に迷う場合は残置を優先）。

## 5. 理由・設計意図

- 一括ダンプ方式は 300KB 上限を超えると単純に切り捨てられ、大規模プロジェクトで破綻していた。
  ツール探索方式では LLM が必要な範囲だけ `read_file`/`search_code` するため、この上限に
  実質的に縛られなくなる（個別ファイルの 50KB 上限のみ残る）。
- `read_file`/`search_code` は **例外を投げず文字列で失敗を返す**方針とした。ADK の
  FunctionTool は戻り値がそのまま LLM への Function Response になるため、例外送出だと
  ツール呼び出し自体がエラー扱いになり LLM が回復困難になる。エラーメッセージ文字列であれば
  LLM が「このパスは存在しない、別を試す」といった継続判断ができる。

## 6. 注意点・エッジケース

- `read_file` で `blob.exists()` が False のケースと、存在するが 50KB 超のケースを区別して
  メッセージを出し分けている。LLM が原因を理解し次の行動を選べるようにするため。
- `search_code` の `pattern` はユーザー入力由来ではなく LLM が生成する正規表現。
  `re.error` を捕捉しているため、不正な正規表現でツール呼び出し自体が失敗することはない。
- `blob.size` は `list_blobs` 経由なら基本的に設定済みだが、`read_file` は
  `bucket.blob(...)` で直接構築するため `blob.reload()` を呼ばないと `size` が None になる点に注意。

## 7. この編集単位の完了条件

- [ ] `load_project_context` / `load_project_context_for_source` がファイルから削除されている。
- [ ] `list_files` / `read_file` / `search_code` が上記シグネチャ・挙動で実装されている。
- [ ] `python -c "from src.services import gcs_client"` が例外なく通る（import 単体確認）。
- [ ] 単体テスト（[05-tests.md](05-tests.md) の `tests/test_tools.py`）がこの時点でまだ無くても可
      （05 で作成）。ただし 01 完了後に手動で `list_files("")` 等を呼び、`GCS_BUCKET` 未設定時に
      空リスト/エラー文字列が返ることを確認しておくと後続の切り分けが楽になる。

## 8. 依存

- なし。最初に着手してよい。
