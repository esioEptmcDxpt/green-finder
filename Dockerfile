# ベースイメージとしてPython 3.9を使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# アプリケーションのソースコード全体をコピー
COPY . .

# Pythonパッケージをインストール
RUN pip install -e .

# Streamlitのポートを公開
EXPOSE 8501

# Streamlitを起動（ヘルスチェック用のログ出力を追加）
CMD ["streamlit", "run", "Hello_OHC_System.py", "--server.address=0.0.0.0", "--server.headless=true"]
