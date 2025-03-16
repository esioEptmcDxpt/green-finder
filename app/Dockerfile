# ビルドステージ
FROM python:3.9-slim AS builder

# 作業ディレクトリを設定
WORKDIR /app

# ビルドに必要なパッケージのみインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtのみをコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# 実行ステージ
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 実行時に必要な最小限のパッケージをインストール
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ビルドステージから必要なファイルをコピー
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# アプリケーションのソースコードをコピー
COPY . .

# Streamlitのポートを公開
EXPOSE 8501

# Streamlitを起動
CMD ["streamlit", "run", "Hello_CIS.py", "--server.address=0.0.0.0", "--server.port=8501"]
