# API Gateway + Lambda認証機能の実装手順

## 概要

ECS環境からCognitoへの直接接続がネットワーク上の制約で困難なため、API Gateway + Lambdaを使用した認証プロキシを実装します。このプロキシはCognitoの認証処理を代行し、アプリケーションとCognito間の通信を仲介します。

## セットアップ手順

### 1. Lambda関数のデプロイ

1. AWSマネジメントコンソールにログインし、Lambda サービスに移動します。
2. 「関数の作成」を選択します。
3. 「一から作成」を選択し、以下の情報を入力します：
   - 関数名: `cis-auth-proxy`
   - ランタイム: `Python 3.9`
   - アーキテクチャ: `x86_64`
4. 「関数の作成」ボタンをクリックします。
5. 作成された関数の画面で、`lambda_auth_function.py` のコードをコピーして関数コードエディターに貼り付けます。
6. 「デプロイ」ボタンをクリックします。

### 2. Lambda関数の環境変数の設定

1. Lambda関数の「環境変数」セクションで以下の変数を設定します：
   - `REGION`: `ap-northeast-1`
   - `USER_POOL_ID`: `ap-northeast-1_OPZscsccQ`
   - `CLIENT_ID`: CognitoアプリクライアントのクライアントID
   - `CLIENT_SECRET`: Cognitoアプリクライアントのクライアントシークレット
   - `REDIRECT_URI`: コールバックURL（例: `https://your-app-domain.com/auth/callback`）
   - `COGNITO_DOMAIN`: CognitoドメインURLのホスト部分（例: `your-domain.auth.ap-northeast-1.amazoncognito.com`）

### 3. Lambda関数のIAMロールの設定

1. Lambda関数の「設定」タブ→「アクセス権限」をクリックします。
2. 表示されるIAMロールの名前をクリックして、IAMコンソールに移動します。
3. 「ポリシーのアタッチ」ボタンをクリックします。
4. 「ポリシーの作成」を選択します。
5. JSONタブに切り替えて、`lambda_policy.json` の内容を貼り付けます。
6. 「次へ」をクリックして、ポリシー名（例: `CisAuthProxyPolicy`）を入力し、「ポリシーの作成」をクリックします。
7. 作成したポリシーを選択し、「ポリシーのアタッチ」をクリックします。

### 4. API Gatewayの作成

1. API Gatewayサービスに移動します。
2. 「APIの作成」をクリックします。
3. 「REST API」を選択し、「構築」をクリックします。
4. APIの詳細を入力します：
   - API名: `cis-auth-api`
   - 説明: `CIS認証プロキシAPI`
   - エンドポイントタイプ: `リージョン`
5. 「APIの作成」をクリックします。

### 5. リソースとメソッドの作成

以下のエンドポイントを作成します：

#### 5.1 `/auth/login` エンドポイントの作成

1. 「リソースの作成」をクリックし、リソース名を `auth` と入力して作成します。
2. 作成した `auth` リソースを選択し、再度「リソースの作成」をクリックします。
3. リソース名を `login` と入力し、作成します。
4. `login` リソースを選択し、「メソッドの作成」をクリックします。
5. メソッドタイプに `GET` を選択し、以下の設定を行います：
   - 統合タイプ: `Lambda関数`
   - Lambda関数: `cis-auth-proxy`
6. 「保存」をクリックします。

#### 5.2 その他のエンドポイントの作成

同様の手順で以下のエンドポイントを作成します：

- `/auth/callback` (GET)
- `/auth/token` (POST)
- `/auth/validate` (GET)
- `/auth/logout` (POST)

### 6. APIのデプロイ

1. 「アクション」ドロップダウンから「APIのデプロイ」を選択します。
2. 新しいステージ名を `prod` と入力し、「デプロイ」をクリックします。
3. デプロイ後に表示される呼び出しURLをメモします（例: `https://abcdefg123.execute-api.ap-northeast-1.amazonaws.com/prod`）。

### 7. CORSの設定

1. API Gatewayコンソールで、作成したAPIを選択します。
2. 「リソース」セクションで、「アクション」ドロップダウンから「CORSの有効化」を選択します。
3. 以下の設定を行います：
   - アクセス制御を許可するオリジン: `*`（または特定のアプリケーションドメイン）
   - アクセス制御を許可するヘッダー: `Content-Type,Authorization`
   - アクセス制御を許可するメソッド: `GET,POST,OPTIONS`
4. 「CORSの有効化とプリフライトのデフォルト有効化」をクリックします。
5. 「アクション」ドロップダウンから「APIのデプロイ」を再度選択し、ステージ `prod` を選択して「デプロイ」をクリックします。

### 8. アプリケーションの設定変更

1. `auth_lambda_client.py` ファイルをアプリケーションプロジェクトに追加します。
2. 環境変数 `AUTH_API_ENDPOINT` を設定してAPI GatewayのエンドポイントURLを指定します（例: `https://abcdefg123.execute-api.ap-northeast-1.amazonaws.com/prod`）。
3. アプリケーションが認証に使用している既存の `auth.py` を `auth_lambda_client.py` の内容で置き換えるか、インポート先を変更します。

## トラブルシューティング

### Lambda関数のテスト

Lambdaコンソールでテストイベントを作成して関数をテストできます。以下はテスト用のJSONイベントの例です：

```json
{
  "resource": "/auth/login",
  "path": "/auth/login",
  "httpMethod": "GET",
  "headers": {},
  "queryStringParameters": null,
  "pathParameters": null,
  "stageVariables": null,
  "body": null,
  "isBase64Encoded": false
}
```

### APIのテスト

API Gatewayコンソールでテストタブを使用して各エンドポイントをテストできます。または、curl、Postmanなどのツールを使用して、デプロイされたAPIエンドポイントにリクエストを送信できます。

### ログの確認

問題が発生した場合、CloudWatch Logsで Lambda関数のログを確認してください。
