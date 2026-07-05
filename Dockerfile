FROM python:3.13-slim

WORKDIR /app

# 依存パッケージのインストール（レイヤーキャッシュ活用）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# Cloud Run は PORT 環境変数を自動的にセットする
ENV PORT=8080

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
