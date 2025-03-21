# Contact-wire Inspection System ~ トロリ線摩耗判定支援システム ~

このシステムは、検測車(East-i)で撮影した電車線金具モニタリング画像を利用して、トロリ線の局部摩耗を探索することをサポートするアプリです。

このアプリは AWS クラウド上で構築することを想定しています。もしローカル環境で Streamlit を実行する場合は、AWS CLI の設定が必要になりますので、管理者に問い合わせてください。

# 開発者向け

## アプリの更新方法

最初にリポジトリをクローンします。
プライベートリポジトリのため、認証情報は管理者に問い合わせること。

```bash
git clone https://github.com/ESIO-EPTMC-DXPT/contact-wire-inspection-system.git
cd ./contact-wire-inspection-system
```

### ECRにコンテナをプッシュ

アプリを更新したら、ECR に更新後のコンテナイメージをプッシュします。（プロジェクトのルートディレクトリで実行すること）

```bash
source ecr-push.sh
```

## ローカル環境での利用方法

1. シークレット情報を準備する
   以下を参考に、 `app/.streamlit/secrets.toml` を作成します。

全て AWS Cognito の設定値なので、マネジメントコンソールにアクセスして確認しましょう。不明な場合は、管理者に問い合わせてください。

```toml
[cognito]
client_id = "<your-client-id>"
client_secret = "<your-client-secret>"
aws_region = "ap-northeast-1"
user_pool_id = "<your-user-pool-id>"
domain = "<your-cognito-domain>"
redirect_uri = "http://localhost:8501"
```

2. アプリ実行用のコンテナを起動する

認証情報を設定したら、アプリ実行用のコンテナを起動します。

```bash
docker-compose up
```

2. アプリにアクセスする

アプリがローカルホスト (http://localhost:8501) で起動するので、ブラウザでアクセスします。

3. アプリを終了する

コンテナでアプリを実行中は、ターミナルに標準出力が表示されています。
アプリを終了するときは `Ctrl + C` を押してください。

## (開発用)ディレクトリ構造

```
.
├── README.md                            # Readme
├── README_forStreamlit.ipynb            # 使い方の説明＆実行用　　　　※不要であれば削除する
├── Hello_OHC_System.py               # Streamlit スタートページ
├── pages                                # Streamlit 各コードのメインファイル
│   ├── 1_⚡_摩耗判定システム.py          # 摩耗判定メインファイル
│   ├── 2_📸_出力画像をチェックする.py    # 結果画像を表示　（機能改修のため、一時的に無効化中）
│   ├── 3_📈_解析データをチェックする.py   # 結果をCSV出力し、グラフを表示
│   ├── 4_🔎_異常箇所をチェックする.py    # 異常摩耗箇所をチェックする　※未実装
│   ├── 98_📝_解析ログ操作.py            # 摩耗判定システムの操作ログを確認する
│   └── 99_🍣_python_コードを見る.py     # (おまけ) コード参照用
├── config.yml                           # appの各種設定値格納ファイル
├── src
│   ├── __init__.py                      # 読み込み用初期化ファイル
│   ├── kalman_calc.py                   # カルマンフィルタ計算用のラッパーファイル
│   ├── similar_pixel_calc.py            # 類似ピクセル計算用のラッパーファイル
│   ├── trolley.py                       # トロリ線パラメータ用クラス用ファイル
│   ├── visualize.py                     # 可視化用ファイル
│   ├── config.py                        # 設定パラメータ処理用ファイル
│   ├── helpers.py                       # 読み込み・リストなどのUtil処理用ファイル
│   ├── kalman.py                        # カルマンフィルタの計算用コアクラス用ファイル
│   └── similar_pixel.py                 # 類似ピクセルの計算用コアクラス用ファイル
├── imgs                                 # 画像ファイル
├── output                               # 出力ファイル
├── TDM                                  # 画像ファイル名→キロ程変換情報を管理
├── test                                 # テスト用ディレクトリ
│   └── test.py                          # テスト用ファイル
└── utils                                # データ検証用
```

## (開発用)改善点の要点：

今後のアプリ化を容易にしつつ、継続的な改変を行うため、以下に留意して改善

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
