# RTG Coding Agent 仕様書

**バージョン**: v0.5.0 / **作成日**: 2026-06-29

---

## 1. 役割

GCS に保存されたソースコードを Vertex AI で分析し、実装計画を生成する。  
入力元・出力先はともに RTG（findy-hackathon-202604-pre）。危険度判定・試験・段位管理は RTG の責務であり、CodingAgent は関与しない。

```
RTG → CodingAgent（本リポジトリ）→ RTG
```

---

## 2. 入出力

### Input: `POST /generate`

```json
{
  "input_text": "商品テーブルに stock_reserved カラムを追加したい",
  "target_source": "gcs:mori-market",
  "target_context": ""
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `input_text` | `str` | ユーザーの変更要求（自然言語）|
| `target_source` | `str` | `gcs:<project_id>` → Firestore + GCS からコードを取得 |
| `target_context` | `str` | コード文脈の直接指定（`target_source` より優先） |

### Output: `GenerationResult`

```json
{
  "explanation": "Product モデルに stock_reserved カラムを追加し、Alembic でマイグレーションを行います。",
  "file_changes": [
    {
      "path": "src/models/product.py",
      "description": "stock_reserved フィールドを追加",
      "content": "from sqlalchemy import Column, Integer\n\nclass Product(Base):\n    ...\n    stock_reserved = Column(Integer, default=0)\n"
    }
  ],
  "commands": [
    "alembic revision --autogenerate -m 'add_stock_reserved'",
    "alembic upgrade head",
    "pytest tests/test_order_service.py -v"
  ]
}
```

| フィールド | 型 | 説明 |
|---|---|---|
| `explanation` | `str` | 実装方針の自然言語説明 |
| `file_changes` | `list[FileChange]` | 変更するファイル一覧 |
| `commands` | `list[str]` | 実行するコマンド（順序通り）|

`FileChange`:

| フィールド | 型 | 説明 |
|---|---|---|
| `path` | `str` | ファイルパス |
| `description` | `str` | 変更内容の説明 |
| `content` | `str \| None` | 変更後のファイル内容 |
| `diff` | `str \| None` | unified diff 形式（`content` と排他）|

---

## 3. 技術スタック

| 技術 | 用途 |
|---|---|
| **Google Cloud Storage** | ソースコードのストレージ（`gs://<bucket>/<project_id>/` 以下） |
| **Cloud Firestore** | プロジェクトメタデータ（name / gcs_bucket / language / framework 等）|
| **Vertex AI（Gemini）** | コード分析・実装計画生成（ADK LlmAgent 経由）|
| **FastAPI** | REST サーバー |

Vertex AI バックエンドの切り替えは環境変数 `GOOGLE_GENAI_USE_VERTEXAI=1` のみ。認証は ADC。

### Firestore スキーマ

コレクション `coding_projects/{project_id}`:

```
name: str          プロジェクト名
description: str   概要
gcs_bucket: str    ソースコードの GCS バケット名
gcs_prefix: str    GCS プレフィックス（通常 "<project_id>/"）
language: str      主要言語
framework: str     フレームワーク
created_at: Timestamp
```

### GCS 制約

- スキップ対象: `.png` `.pyc` `.zip` 等のバイナリ・生成物
- 1 ファイル上限: 50 KB
- コード文脈全体の上限: 300 KB

---

## 4. ディレクトリ構成

```
rtg-coding-agent/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── agents/coding_agent.py        # ADK LlmAgent
│   ├── routers/generate.py           # POST /generate
│   ├── schemas/plan.py               # GenerationRequest / FileChange / GenerationResult
│   └── services/
│       ├── gcs_client.py             # GCS からコード取得
│       └── firestore_client.py       # Firestore からメタデータ取得
├── tests/
├── spec/coding-agent-spec.md
├── requirements.txt
└── .env.example
```

---

## 5. 実装タスク

### CodingAgent（本リポジトリ）

| ID | 内容 | 成果物 |
|---|---|---|
| CA-01 | プロジェクト初期化 | `main.py` `config.py` `requirements.txt` |
| CA-02 | スキーマ定義 | `schemas/plan.py` |
| CA-03 | Firestore クライアント | `services/firestore_client.py` |
| CA-04 | GCS クライアント | `services/gcs_client.py` |
| CA-05 | ADK LlmAgent 実装 | `agents/coding_agent.py` |
| CA-06 | `POST /generate` エンドポイント | `routers/generate.py` |
| CA-07 | 単体テスト | `tests/` |

### RTG 側の対応（findy-hackathon-202604-pre）

| ID | 内容 | 変更ファイル |
|---|---|---|
| RTG-CA-01 | CodingAgent HTTP クライアント追加 | `services/coding_agent_client.py`（新規）|
| RTG-CA-02 | `ImplementationPlan` → `InterpretationResult` 変換アダプタ追加 | `services/interpretation_adapter.py`（新規）|
| RTG-CA-03 | `interpreter.py` に切り替えロジック追加（`CODING_AGENT_URL` 未設定なら既存の Gemini 直呼びを維持）| `agents/interpreter.py`（改修）|

#### アダプタの変換ルール

`GenerationResult` から RTG の `InterpretationResult` を組み立てる。  
`domain` は N-01c（ドメイン分類 Agent）に委ねるため空文字、`level_hint` は N-03 に委ねるため 0 を渡す。

```python
def adapt(result: dict) -> InterpretationResult:
    # ファイル変更の説明とコマンドを commands リストに統合
    commands = (
        [fc["description"] for fc in result.get("file_changes", [])]
        + result.get("commands", [])
    )
    return InterpretationResult(
        commands=commands,
        domain="",     # N-01c が分類
        level_hint=0,  # N-03 LLM Gatekeeper が判定
    )
```

---

## 6. 環境変数

### CodingAgent

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1
GEMINI_MODEL=gemini-2.0-flash
GCS_BUCKET=rtg-coding-agent-sources
# FIRESTORE_EMULATOR_HOST=localhost:8080  # ローカル開発時
PORT=8001
```

### RTG 側の追加

```bash
CODING_AGENT_URL=http://localhost:8001  # 未設定なら既存の Gemini 直呼びを維持
```
