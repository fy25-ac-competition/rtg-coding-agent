# RTG Coding Agent

逆チューリングゲート（RTG）のコーディングエージェント外部実装。  
RTG 本体から A2A JSON-RPC 2.0 形式でリクエストを受け取り、Vertex AI (Gemini) でテキスト回答を生成して返す。

```
RTG 本体 (FastAPI) ──A2A JSON-RPC 2.0──▶ rtg-coding-agent (本リポジトリ)
                                              │
                                    Vertex AI (Gemini)
                                              │
                           GCS（demo アプリのソースコード）
```

---

## CA メソッド対応表

RTG から受け取る質問テキストのパターンと、CA が返す回答形式:

| メソッド | 質問テキスト先頭パターン | 回答形式 |
|---|---|---|
| `create_spec` | "以下の要望を実現する spec ファイル…" | Markdown spec 全文 |
| `edit_spec` | "以下の現行 spec を…更新し…" | 更新後 Markdown spec |
| `generate_command_list` | "以下の spec を実現するために実行すべきコマンドを…" | 1行1コマンド（生テキスト） |
| `investigate_impact` | "以下のコマンドが対象システムに与える影響を…" | 影響調査報告文 |
| `notify_approval` | "以下のコマンドが承認されました。模擬実行し…" | 模擬実行結果報告文 |
| `notify_rejection` | "以下のコマンドは拒否されました…" | 確認応答テキスト |
| `suggest_usecases` | "以下の対象ソースを分析し、ユーザーが…候補を…" | 1行1件（2〜3件） |

> `metadata.target_source`（例: `demo:system-m`）が付与された場合、GCS からそのデモアプリのソースコードを読み込んで質問に付加する。

---

## ディレクトリ構成

```
rtg-coding-agent/
├── src/
│   ├── main.py                  # FastAPI アプリ
│   ├── config.py                # 環境変数
│   ├── agents/
│   │   └── coding_agent.py      # ADK LlmAgent（テキスト応答）
│   ├── routers/
│   │   └── a2a.py               # POST / A2A エンドポイント
│   ├── schemas/
│   │   └── a2a.py               # A2A リクエスト/レスポンス スキーマ
│   └── services/
│       └── gcs_client.py        # GCS からソースコードを読み込む
├── tests/
│   └── test_a2a.py
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## ローカル開発

### 前提

- Python 3.11 以上
- Google Cloud SDK（`gcloud` コマンド）
- ADC 認証済み: `gcloud auth application-default login`

### セットアップ

```bash
# 依存インストール
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install pytest httpx           # テスト用

# 環境変数の設定
cp .env.example .env
# .env を編集して GOOGLE_CLOUD_PROJECT、GCS_BUCKET 等を設定
```

### サーバー起動

```bash
source venv/bin/activate
uvicorn src.main:app --reload --port 8001
# → http://localhost:8001
# → http://localhost:8001/docs (Swagger UI)
```

RTG 本体側で `A2A_CODING_AGENT_URL=http://localhost:8001` を設定すると接続される。

### テスト実行

```bash
# google.* が未インストールでも動く（テスト内でスタブ化済み）
pytest tests/ -v
```

---

## 環境変数

| 変数名 | 必須 | 説明 |
|---|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI` | ✅ | `1` に設定すると ADK が Vertex AI バックエンドを使用 |
| `GOOGLE_CLOUD_PROJECT` | ✅ | GCP プロジェクト ID |
| `GOOGLE_CLOUD_LOCATION` | ✅ | Vertex AI リージョン（例: `us-central1`） |
| `GEMINI_MODEL` | — | 使用する Gemini モデル（デフォルト: `gemini-2.5-flash`） |
| `GCS_BUCKET` | — | デモアプリのソースコードを格納した GCS バケット名。未設定時はコード文脈なしで動作 |
| `PORT` | — | サーバーポート（デフォルト: Cloud Run では自動設定） |

---

## GCS へのデモアプリソースコードのアップロード

`metadata.target_source: "demo:system-m"` のような識別子を使う場合、GCS に以下の構造でソースコードを配置する:

```
gs://<GCS_BUCKET>/
  system-m/          ← demo:system-m に対応
    index.html
    assets/
      js/cart.js
      ...
  system-s/          ← demo:system-s に対応
    index.html
    ...
```

RTG プロジェクトの `src/demo-app/` にあるファイルをアップロードする:

```bash
# バケット作成（既存バケットがある場合はスキップ）
gcloud storage buckets create gs://<GCS_BUCKET> \
  --project=<PROJECT_ID> \
  --location=us-central1

# demo-app のソースを一括アップロード
# RTG リポジトリの src/demo-app/ をカレントとして実行
gcloud storage cp -r system-m/ gs://<GCS_BUCKET>/system-m/
gcloud storage cp -r system-s/ gs://<GCS_BUCKET>/system-s/
```

---

## Cloud Run へのデプロイ

### 1. Artifact Registry リポジトリを作成

```bash
gcloud artifacts repositories create rtg-coding-agent \
  --repository-format=docker \
  --location=us-central1 \
  --project=<PROJECT_ID>
```

### 2. Docker イメージをビルド & プッシュ

```bash
export PROJECT_ID=<your-gcp-project-id>
export REGION=us-central1
export IMAGE=us-central1-docker.pkg.dev/${PROJECT_ID}/rtg-coding-agent/rtg-coding-agent:latest

# Artifact Registry へ認証
gcloud auth configure-docker us-central1-docker.pkg.dev

# ビルド & プッシュ（Mac Apple Silicon は --platform linux/amd64 が必要）
docker build --platform linux/amd64 -t ${IMAGE} .
docker push ${IMAGE}
```

### 3. サービスアカウントの準備

```bash
# サービスアカウント作成（既存を使う場合はスキップ）
gcloud iam service-accounts create rtg-coding-agent-sa \
  --display-name="RTG Coding Agent SA" \
  --project=<PROJECT_ID>

SA_EMAIL="rtg-coding-agent-sa@<PROJECT_ID>.iam.gserviceaccount.com"

# Vertex AI の使用権限
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

# GCS の読み取り権限
gcloud storage buckets add-iam-policy-binding gs://<GCS_BUCKET> \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"
```

### 4. Cloud Run へデプロイ

```bash
gcloud run deploy rtg-coding-agent \
  --image=${IMAGE} \
  --region=us-central1 \
  --platform=managed \
  --service-account=${SA_EMAIL} \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=<PROJECT_ID>,GOOGLE_CLOUD_LOCATION=us-central1,GEMINI_MODEL=gemini-2.5-flash,GCS_BUCKET=<GCS_BUCKET>" \
  --allow-unauthenticated \
  --project=<PROJECT_ID>
```

> **認証について**: 本番環境では `--allow-unauthenticated` を外し、RTG 本体のサービスアカウントに `roles/run.invoker` を付与して認証付きで呼び出すことを推奨。

### 5. デプロイ確認

```bash
# デプロイされた URL を取得
SERVICE_URL=$(gcloud run services describe rtg-coding-agent \
  --region=us-central1 \
  --format='value(status.url)' \
  --project=<PROJECT_ID>)

echo "CA URL: ${SERVICE_URL}"

# 疎通確認（A2A 形式）
curl -X POST "${SERVICE_URL}/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"text": "以下の要望を実現する spec ファイル（Markdown・実現方針/変更範囲/手順）を作成してください:\nカート画面にクーポン機能を追加したい"}]
      }
    }
  }'
```

### 6. RTG 本体への設定

Cloud Run サービスの URL を RTG 本体の環境変数に設定する:

```bash
# RTG 本体（Cloud Run）の環境変数に追加
gcloud run services update <RTG_SERVICE_NAME> \
  --region=us-central1 \
  --update-env-vars="A2A_CODING_AGENT_URL=${SERVICE_URL}" \
  --project=<PROJECT_ID>
```

---

## A2A ワイヤ形式リファレンス

### リクエスト

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [{ "text": "<質問テキスト>" }],
      "metadata": { "target_source": "demo:system-m" }
    }
  }
}
```

`metadata` は省略可能（後方互換）。

### レスポンス

```json
{
  "result": {
    "artifacts": [
      { "parts": [{ "text": "<回答テキスト>" }] }
    ]
  }
}
```
