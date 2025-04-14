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

# GitHub の設定

## 初めて使う場合の設定 (GitHubでSSH認証を設定する手順)

### 1. SSH鍵を生成する

```bash
# SSH鍵を生成（メールアドレスは自分のJoi-Netアドレスに変更してください）
ssh-keygen -t ed25519 -C "your_email@example.com"

# または、古いシステムでed25519がサポートされていない場合
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

生成時に表示される質問:
- 鍵の保存場所（デフォルトでOK: Enter）
- パスフレーズ（任意: セキュリティ向上のため設定推奨）

### 2. SSH鍵をSSHエージェントに追加する

```bash
# SSHエージェントをバックグラウンドで起動
eval "$(ssh-agent -s)"

# SSH鍵をエージェントに追加
ssh-add ~/.ssh/id_ed25519  # または ~/.ssh/id_rsa
```

### 3. 公開鍵をGitHubに追加する

```bash
# 公開鍵をクリップボードにコピー
cat ~/.ssh/id_ed25519.pub  # または ~/.ssh/id_rsa.pub
```

表示された内容をコピーして:

1. GitHubにログイン
2. 右上のプロフィールアイコン → Settings をクリック
3. 左側のサイドバーで「SSH and GPG keys」をクリック
4. 「New SSH key」ボタンをクリック
5. タイトルに識別しやすい名前（例: 「Work Laptop」）を入力
6. 「Key」フィールドに先ほどコピーした公開鍵を貼り付け
7. 「Add SSH key」をクリック

### 4. リモートURLをSSH形式に変更する

```bash
# 現在のリモートURLを確認
git remote -v

# リモートURLをSSH形式に変更
git remote set-url origin git@github.com:esioEptmcDxpt/green-finder.git
```

### 5. 接続をテストする

```bash
ssh -T git@github.com
```

「Hi username! You've successfully authenticated...」というメッセージが表示されれば成功です。

### 6. プッシュしてみる

```bash
git push --set-upstream origin dev-sio
```

注意: 初回接続時にホストの信頼性確認メッセージが表示されることがありますが、「yes」と入力して続行してください。