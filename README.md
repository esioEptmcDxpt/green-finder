<div markdown="1" align="center">
<h1>Contact-wire Inspection System

〜 トロリ線摩耗判定支援システム 〜</h1>

このシステムは、検測車(East-i)で撮影した電車線金具モニタリング画像を利用して、トロリ線の局部摩耗を探索することをサポートするアプリです。

このアプリは AWS クラウド上で構築することを想定しています。もしローカル環境で Streamlit を実行する場合は、AWS CLI の設定が必要になりますので、管理者に問い合わせてください。

</div>

# ユーザ向けガイド

## アプリの起動方法

アプリは https://esio-cis.com にアクセスすると起動できます。

## アプリの利用方法

アプリには以下の機能があります。

1. 摩耗判定システム
2. 解析結果閲覧システム
3. データ管理
4. ストレージビューワ（参考：開発者向け）
5. 解析ログ操作

# 開発者向け

このアプリのアーキテクチャは以下のようになっています。

![アーキテクチャ](docs/cis_dev.png)

## コードをリポジトリから Clone する

最初にリポジトリをクローンします。
プライベートリポジトリのため、http接続でCloneするにはTokenが必要になります。

GitHubのTokenを取得する方法は[参考になるサイト](https://dev.classmethod.jp/articles/github-personal-access-tokens/)か、[GitHubの公式ドキュメント](https://docs.github.com/jp/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)を参照して、設定した後に、以下のコマンドを実行します。

```bash
git clone https://github.com/ESIO-EPTMC-DXPT/contact-wire-inspection-system.git
cd ./contact-wire-inspection-system
```

## リポジトリの構造を確認する

リポジトリ内のファイルは以下のようになっています。
現在はStreamlitアプリをコンテナ化して利用しているため、ほとんど app ディレクトリのみを利用しています。

```
.
├── README.md                             # Readme
├── app                                   # Streamlitアプリのディレクトリ
|   ├── CIS_App.py                        # Streamlitアプリのメインファイル
|   ├── Dockerfile                        # コンテナイメージファイル
|   ├── docker-compose.yml                # コンテナの起動用ファイル
|   ├── requirements.txt                  # 依存パッケージのリスト
|   ├── .streamlit                        # streamlitの設定ファイル
|   ├── config.yml                        # アプリの設定ファイル
|   ├── pages                             # 各機能ごとのディレクトリ
|   |    ├── 1_⚡_摩耗判定システム.py         # 摩耗判定メインファイル
|   |    ├── 2_📈_解析結果閲覧システム.py     # グラフ・画像を出力
|   |    ├── 4_🔎_異常箇所をチェックする.py   # 異常摩耗箇所をチェックする　※未実装
|   |    ├── 10_⚙️_データ管理.py             # データ管理メインファイル
|   |    ├── 81_📁_ストレージビューワ.py      # ローカルファイル操作（開発者用）
|   |    ├── 98_📝_解析ログ操作.py           # 操作ログを確認する
|   |    └── 99_🍣_python_コードを見る.py    # (おまけ) コード参照用
|   ├── efs                               # ファイルシステムのマウントポイント (自動作成)
|   |    ├── images                       # 画像ファイル
|   |    ├── output                       # 出力ファイル
|   |    ├── logs                         # ログファイル
|   |    └── TDM                          # 画像ファイル名→キロ程変換情報を管理
|   ├── src                               # コードのソースファイル
|   |    ├── kalman_calc.py               # カルマンフィルタ計算用のラッパーファイル
|   |    ├── kalman.py                    # カルマンフィルタの計算用コアクラス用ファイル
|   |    ├── similar_pixel_calc.py        # 類似ピクセル計算用のラッパーファイル
|   |    ├── similar_pixel.py             # 類似ピクセルの計算用コアクラス用ファイル
|   |    ├── trolley.py                   # トロリ線パラメータ用クラス用ファイル
|   |    ├── helpers.py                   # 読み込み・リストなどのUtil処理用ファイル
|   |    ├── visualize.py                 # 可視化用ファイル
|   |    ├── config.py                    # 設定パラメータ処理用ファイル
|   |    ├── logger.py                    # ログ用ファイル
|   |    ├── auth_aws.py                  # 認証用ファイル(Cognito用)
|   |    ├── auth.py                      # 認証用ファイル(Streamlit-Authenticator用)
|   |    ├── create_yml.py                # ユーザー情報用ファイル(Streamlit-Authenticator)
|   |    └── get_strun_url.py             # ストリングURL用ファイル(Jupyter-notebook用)
|   ├── sh/                               # 管理用のスクリプト
|   └── README_forStreamlit.ipynb         # 使い方の説明＆実行用　※コンテナ化により不要
├── docs/                                 # ドキュメント
├── ecr-push.sh                           # ECRにコンテナをプッシュするスクリプト
├── bin/                                  # cdk用（作成中）
├── lib/                                  # cdk用（作成中）
├── cdk.json                              # cdk用設定ファイル（作成中）
.
.
.
```

## ローカル環境でコンテナを起動してテストする

(前提) AWS CLI の設定は完了していることを確認してください。

アプリへのログイン認証に AWS Cognito を利用しています。 `app/.streamlit/secrets.toml` に認証情報を設定しますが、ECS 環境用の内容となっているため、ローカル用に以下のように設定します。
ただし、ECR にプッシュする前に必ず元に戻しましょう。

```toml
[cognito]
redirect_uri = "http://localhost:8501"
```

コンテナを起動するときには、 app ディレクトリで以下のコマンドを実行します。

```bash
docker-compose build --no-cache
docker-compose up
```

ターミナル上で Docker コンテナが起動したら、 `http://localhost:8501` にアクセスしてアプリを確認します。
コンテナを停止するときは、 `ctrl + c` で停止します。

ターミナル上でコンテナを動作させずに、バックグラウンドで実行したいときは、以下のコマンドを実行します。

```bash
docker-compose up -d
```

コンテナを停止するときは、以下のコマンドを実行します。

```bash
docker-compose down
```

### (参考) Docker コンテナで使用するコマンドのメモ

```bash
# コンテナを停止して削除
docker-compose down

# コンテナイメージを再ビルド
docker-compose build --no-cache

# コンテナを起動
docker-compose up

# コンテナを起動（バックグラウンドで実行）
docker-compose up -d

```

定期的なお掃除用のコマンド
（コンテナイメージでストレージを圧迫しないため）

```bash
# システム全体（未使用のコンテナ含む）のクリーンアップ
docker system prune -a --force
# 使用していないコンテナイメージを削除
docker image prune

# 使用していないシステムリソースの削除
docker system prune

# 強制的に全てのコンテナイメージを削除するときに実行する。
docker rmi $(docker images -q)
```

## ECRにコンテナをプッシュする

開発が完了したら、 `app/.streamlit/secrets.toml` を元に戻した後、以下のスクリプトを実行して ECR にコンテナをプッシュします。
このコマンドはプロジェクトのルートディレクトリ（ `contact-wire-inspection-system` ）で実行します。

```bash
source ./ecr-push.sh
```

## (開発用)メモ

今後のアプリ化を容易にしつつ、継続的な改変を行うため、以下に留意して改善していく。

参考文献：

- https://awesome-streamlit.readthedocs.io/en/latest/index.html
- https://towardsdatascience.com/intermediate-streamlit-d5a1381daa65

1. 変数名：エンドユーザーに分かりやすい名称にフォーマットし、format_func で呼び出す

   - 辞書と組み合わせて値の対応関係を作成しておくのと、format_func=、で呼び出せる。
     候補：camera 種別、画像ディレクトリ置き場のリスト表示
   - 変更の理由
     - Pandas 等の変数名の定義とアプリ表示上の名称が異なるため、その対応関係を整理すると構造的に改変がユーザー、開発者双方に取って容易に理解できるものとなる。

2. キャッシュを用いて読み込み速度を改善

   - アプリで呼び出される関数を細かく分割し、各関数に st.cache デコレータを用いることで読み込み速度を改善
   - キャッシュによる読み込みは update が続いており、現在@st.cache_data と@st.cache_resource に分割
     - https://docs.streamlit.io/library/advanced-features/caching
     - ユースケースに応じて使い分ける。
     - Version upgrade すると動かなくなることがあるので、当面は v1.10 以下を推奨。

3. 動的ウイジェットの作成

   - 何かを選択する際に、後続の処理に影響を与える場合、その挙動を組み込んでおく
     - a, b, c の 3 つを使って散布図を作成したいとする。
     - a を X 軸として選んだ場合、Y 軸の選択肢は b, c のいずれかに絞られるため、それを内部変数として作成しておき、選択肢を Y 軸の選択の選択肢を減らす

4. 定期的にリファクタリング、コードの記述やテストを行う

   - 100 行を超えてくる場合、関数を別の場所から呼び出す
   - ストリームライト関数とヘルパー関数のみをインポートします
   - ストリームライトオブジェクト、つまりビジュアライゼーションやウィジェットに入力されていない変数を、コードの次の行で作成しないでください (データ読み込み関数を除く)

5. black、flake8 など、コード整形と文法チェックを行い、コーディング規約に従って記述
   - コーディングルールを決めておくことで見通しが良くなります。
   - 基本的には black によるコードの自動整形＋ flake8 によるチェックで事足ります。
   - Jupyter notebook 状でのインストール手順は下記を参考にしてください。

## コードフォーマッター black の導入と修正

ここでは Python のコードフォーマットを自動で整形してくれる Black の Jupyter notebook への導入手順と修正手順を示します。

1. Jupyter notebook のマジックコマンド、もしくはターミナルから Black をインストール

```
pip install black
```

2. black を使い、コードの自動フォーマットを実行します。

```
$ black <your testfile>.py
reformatted main.py

All done! ✨ 🍰 ✨
1 file reformatted.
```

上の flake8 と組み合わせチェックすることで、チェック回数やコーディングルールの把握を進めることができます。

## コーディング規約のチェック手順

SageMaker Notebook instance を想定

1. Jupyter notebook からターミナルを起動し、flake8 をインストール

```
pip install flake8
```

2. 文法チェックを行うファイルを指定し、flake8 を実行

```
flake8 <testfile>.py --max-line-length 200
```

- max-line-length は 1 行の長さを制限するものです。pep8 では 79 文字まで、としていますが他の規約に比較し、優先度が落ちるため、長めの文字数に設定します。

3. エラーに従ってファイルを更新します。

```
$ flake8 main.py
main.py:2:1: F401 'openpyxl' imported but unused
```

上記では 2 行目で import されたが使われていないライブラリが存在することを提示してくれます。
各エラーの詳細と修正方針については、公式ページを参照してください。
https://flake8.pycqa.org/en/2.6.0/warnings.html
