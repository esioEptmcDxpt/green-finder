FROM python:3.9-slim

WORKDIR /app

# システムの依存関係をインストール（geopandasに必要なライブラリを含む）
RUN apt-get update && apt-get install -y \
    build-essential \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# 必要なパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードとデータをコピー
COPY ./src /app/src

# Streamlitのポートを公開
EXPOSE 8080

# コンテナ起動時に実行するコマンド
CMD ["streamlit", "run", "src/green_finder.py", "--server.address=0.0.0.0", "--server.port=8501"]

