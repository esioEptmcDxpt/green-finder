# CIS: Contact-wire Inspection System 用のメモ

## デプロイ手順

### 使用していないコンテナイメージを削除する

```bash
docker image prune
```

### (参考)全てのコンテナイメージを削除する

強制的に全てのコンテナイメージを削除するときに実行する。

```bash
docker rmi $(docker images -q)
```

### コンテナを停止して削除 → 再起動

```bash
# dockerファイルが有るディレクトリまで移動する
# 以下はローカル環境の例、環境に合わせてパスを修正して利用する
cd ~Documents/cursor/cis/contact-wire-inspection-system

# コンテナを停止して削除
docker-compose down

# コンテナイメージを再ビルド
docker-compose build --no-cache

# コンテナを起動
docker-compose up -d
```

## ローカル開発環境の設定

### リポジトリをクローンする

プライベートリポジトリのため、認証情報は管理者に問い合わせること。

```bash
git clone https://github.com/ESIO-EPTMC-DXPT/contact-wire-inspection-system.git
cd ./contact-wire-inspection-system
```

### 仮想環境を作る

```bash
python -m venv env_cis
```

### 仮想環境を有効化

```bash
source env_cis/bin/activate
```

### (ローカル開発用) 必要なパッケージをインストール

```bash
pip install -e .
```

## Streamlit を起動

```bash
streamlit run Hello_OHC_System.py
```

## Streamlit を起動

```bash
streamlit run Hello_OHC_System.py
streamlit run Hello_OHC_System.py --server.port=8501
```

## env_tis を有効化して Streamlit を起動

```bash
source env_tis/bin/activate
cd TIS && pip install -e .
streamlit run Hello_OHC_System.py
```

## env_tis を無効化

```bash
deactivate && cd ..
```

# deploy-stremlit-app のメモ

## 環境設定

### AWS CDK のインストール

TIS のディレクトリに移動してから実行

```bash
npm install -g aws-cdk
```

プロジェクトの初期化（最初だけ？）

```bash
# TISディレクトリ内に新しくcdkディレクトリを作成
mkdir cdk
cd cdk

# CDKプロジェクトの初期化
cdk init app --language typescript
```

必要なパッケージをインストールする

```bash
npm install aws-cdk-lib construct
```

# 雑メモ

# プロンプト設計

以下は、今回の CDK スタックコードを生成するためのプロンプトです：

---

## プロンプト：AWS CDK で Streamlit アプリのインフラ構築

AWS CDK を使用して、以下の要件を満たす Streamlit アプリケーション用のインフラストラクチャを構築するコードを作成してください。

# 要件：

1. アプリ名: esio-cis-app
2. カスタムドメイン: esio-cis.com (app.esio-cis.com でアクセス)
3. 以下のコンポーネントを含むアーキテクチャ:
   - Fargate 上で Streamlit アプリを実行
   - EFS を使用してデータ永続化
   - ALB でトラフィック分散
   - CloudFront でコンテンツ配信
   - Route53 でカスタムドメイン設定
   - WAF でセキュリティ保護（SizeRestrictions_BODY ルールはカウントモードに設定）
   - ACM 証明書で HTTPS 化

# 設計上の要件：

1. コードはリファクタリングされ、メソッドに分割されていること
2. 設定値はすべて cdk.json から取得し、環境変数も含めること
3. アプリケーションコードは同じプロジェクト内の「app」ディレクトリに配置すること
4. TypeScript で実装すること

# 出力してほしいもの：

1. プロジェクトのディレクトリ構造
2. lib/esio-cis-app-stack.ts (メインのスタック定義)
3. bin/esio-cis-app.ts (エントリーポイント)
4. cdk.json (設定ファイル)
5. 実装の説明と注意点

---

このプロンプトは、以下の点を考慮して設計されています：

1. **明確な要件定義**: アプリ名、ドメイン名、必要な AWS コンポーネントなど、具体的な要件を明示
2. **設計上の制約**: リファクタリング、設定の外部化、ディレクトリ構造などの設計上の要件を明確化
3. **出力の指定**: 必要なファイルと説明を具体的に要求
4. **技術スタックの明示**: TypeScript と AWS CDK を使用することを明示

このプロンプトを使用することで、今回生成したようなリファクタリングされた高品質な CDK コードを効率的に取得できます。
