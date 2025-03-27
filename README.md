# Green-Finder

マヤ車測定データを可視化するアプリです。

# デプロイ手順

以下を実行してリポジトリをクローンします。

```bash
git clone https://github.com/ESIO-EPTMC-DXPT/green-finder.git
cd g_finder
```

AWS ECS にデプロイ済みのコードを更新するには、以下のコマンドを実行します。

```bash
source deploy.sh
```

# ローカル環境での開発

アプリのコードは `app` ディレクトリに格納されています。

ローカル環境で実行する場合は、 `app` に移動してから、以下のコマンドでコンテナを起動して実行します。

```bash
# docker-compose でコンテナを起動する
# バックグラウンドで実行
docker-compose up --build -d

# ターミナル上で実行、停止するときは ctrl + c で停止させます
docker-compose up
```

開発環境（Cloud9）でコンテナを起動する場合は、 Preview で確認できるポートが限られているので、以下のコマンドを使用します。

```bash
# バックグラウンドで実行
docker-compose -f docker-compose.dev.yml up --build -d
# ターミナル上で実行、停止するときは ctrl + c で停止させます
docker-compose -f docker-compose.dev.yml up
```

## (参考) Docker のコマンド

参考にしたページ: https://qiita.com/yusuke_mrmt/items/e05d7914065824384a6b

起動中のコンテナを確認する

``` bash
docker-compose ps
```

コンテナを停止（データは保持）

``` bash
docker-compose stop
```

コンテナを削除
``` bash
docker-compose down
```

コンテナを完全に削除

``` bash
docker-compose down -v
```

イメージも含めて完全に削除
``` bash
docker-compose down --rmi all
```