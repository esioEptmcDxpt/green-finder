# JR東日本_トロリ線画像判別アプリ構築
## ディレクトリ構造
```
.
├── README.md                          # Readme
├── README_forStreamlit.ipynb          # 使い方の説明＆実行用　　　　※不要であれば削除する
├── app.py                             # Streamlit スタートページ
├── pages                              # Streamlit 各コードのメインファイル
│   ├── 1_⚡_摩耗判定システム.py       # 摩耗判定メインファイル
│   ├── 2_📸_出力画像をチェックする.py # 結果画像を表示
│   ├── 3_📈_グラフをチェックする.py   # 結果グラフを表示　　　　　　※未実装
│   ├── 4_🔎_異常箇所をチェックする.py # 異常摩耗箇所をチェックする　※未実装
│   └── 99_🍣_python_コードを見る.py   # コード参照用
├── requirements.txt                   # ライブラリ
├── config.yml                         # appの各種設定値格納ファイル
├── src
│   ├── __init__.py                    # 読み込み用初期化ファイル
│   ├── kalman_calc.py                 # カルマンフィルタ計算用のラッパーファイル
│   ├── similar_pixel_calc.py          # 類似ピクセル計算用のラッパーファイル
│   ├── trolley.py                     # トロリ線パラメータ用クラス用ファイル
│   ├── visualize.py                   # 可視化用ファイル
│   ├── config.py                      # 設定パラメータ処理用ファイル
│   ├── helpers.py                     # 読み込み・リストなどのUtil処理用ファイル
│   └── kalman.py                      # カルマンフィルタの計算用コアクラス用ファイル
├── imgs                               # 画像ファイル
├── output                             # 出力ファイル
└── test                               # テスト用ディレクトリ
    └── test.py                        # テスト用ファイル
```

## 改善点の要点：
今後のアプリ化を容易にしつつ、継続的な改変を行うため、以下に留意して改善

参考文献：
* https://awesome-streamlit.readthedocs.io/en/latest/index.html
* https://towardsdatascience.com/intermediate-streamlit-d5a1381daa65

1. 変数名：エンドユーザーに分かりやすい名称にフォーマットし、format_funcで呼び出す
    * 辞書と組み合わせて値の対応関係を作成しておくのと、format_func=、で呼び出せる。
    候補：camera種別、画像ディレクトリ置き場のリスト表示
    * 変更の理由
        * Pandas等の変数名の定義とアプリ表示上の名称が異なるため、その対応関係を整理すると構造的に改変がユーザー、開発者双方に取って容易に理解できるものとなる。

2. キャッシュを用いて読み込み速度を改善
    * アプリで呼び出される関数を細かく分割し、各関数にst.cache デコレータを用いることで読み込み速度を改善
    * キャッシュによる読み込みはupdateが続いており、現在@st.cache_dataと@st.cache_resourceに分割
        * https://docs.streamlit.io/library/advanced-features/caching
        * ユースケースに応じて使い分ける。
        * Version upgradeすると動かなくなることがあるので、当面はv1.10以下を推奨。

3. 動的ウイジェットの作成
    * 何かを選択する際に、後続の処理に影響を与える場合、その挙動を組み込んでおく
        * a, b, cの3つを使って散布図を作成したいとする。
        * aをX軸として選んだ場合、Y軸の選択肢はb, cのいずれかに絞られるため、それを内部変数として作成しておき、選択肢をY軸の選択の選択肢を減らす

4. 定期的にリファクタリング、コードの記述やテストを行う
    * 100行を超えてくる場合、関数を別の場所から呼び出す
    * ストリームライト関数とヘルパー関数のみをインポートします
    * ストリームライトオブジェクト、つまりビジュアライゼーションやウィジェットに入力されていない変数を、コードの次の行で作成しないでください (データ読み込み関数を除く)

5. black、flake8など、コード整形と文法チェックを行い、コーディング規約に従って記述
    * コーディングルールを決めておくことで見通しが良くなります。
    * 基本的にはblackによるコードの自動整形＋flake8によるチェックで事足ります。
    * Jupyter notebook状でのインストール手順は下記を参考にしてください。

## コードフォーマッターblackの導入と修正
ここではPythonのコードフォーマットを自動で整形してくれるBlackのJupyter notebookへの導入手順と修正手順を示します。

1. Jupyter notebookのマジックコマンド、もしくはターミナルからBlackをインストール
```
pip install black
```

2. blackを使い、コードの自動フォーマットを実行します。
```
$ black <your testfile>.py
reformatted main.py

All done! ✨ 🍰 ✨
1 file reformatted.
```
上のflake8と組み合わせチェックすることで、チェック回数やコーディングルールの把握を進めることができます。

## コーディング規約のチェック手順
SageMaker Notebook instanceを想定

1. Jupyter notebookからターミナルを起動し、flake8をインストール
```
pip install flake8
```

2. 文法チェックを行うファイルを指定し、flake8を実行
```
flake8 <testfile>.py --max-line-length 200
```
* max-line-lengthは1行の長さを制限するものです。pep8では79文字まで、としていますが他の規約に比較し、優先度が落ちるため、長めの文字数に設定します。

3. エラーに従ってファイルを更新します。
```
$ flake8 main.py
main.py:2:1: F401 'openpyxl' imported but unused
```
上記では2行目でimportされたが使われていないライブラリが存在することを提示してくれます。
各エラーの詳細と修正方針については、公式ページを参照してください。
https://flake8.pycqa.org/en/2.6.0/warnings.html