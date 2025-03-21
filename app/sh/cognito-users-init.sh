# ユーザー作成スクリプト
# (参考)source sh/cognito-users-init.sh で実行可能
# (参考)このスクリプトに実行権限を付与する場合は、予め chmod +x sh/cognito-users-init.sh を実行しておく

USER_POOL_ID="ap-northeast-1_OPZscsccQ"  # ユーザープールIDを指定
PERMANENT_PASSWORD="cisUser#2025"  # すべてのユーザーの正式パスワード

# ユーザーリスト
USERS=(
  "shinagawa,cisUser#202503,hoge@jreast.co.jp"
  "shinjuku,cisUser#202503,hoge@jreast.co.jp"
  "ueno,cisUser#202503,hoge@jreast.co.jp"
  "yokohama,cisUser#202503,hoge@jreast.co.jp"
  "hachioji,cisUser#202503,hoge@jreast.co.jp"
  "oomiya,cisUser#202503,hoge@jreast.co.jp"
  "takasaki,cisUser#202503,hoge@jreast.co.jp"
  "mito,cisUser#202503,hoge@jreast.co.jp"
  "chiba,cisUser#202503,hoge@jreast.co.jp"
  "nagano,cisUser#202503,hoge@jreast.co.jp"
  "sendai,cisUser#202503,hoge@jreast.co.jp"
  "morioka,cisUser#202503,hoge@jreast.co.jp"
  "akita,cisUser#202503,hoge@jreast.co.jp"
  "niigata,cisUser#202503,hoge@jreast.co.jp"
)

for user in "${USERS[@]}"; do
  IFS=',' read -r username temp_password email <<< "$user"
  
  echo "ユーザー $username を作成します..."
  
  aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username $username \
    --temporary-password $temp_password \
    --user-attributes Name=email,Value=$email Name=email_verified,Value=true \
    --message-action SUPPRESS
  
  echo "ユーザー $username を作成しました"
  
  # 正式パスワードを設定する
  echo "ユーザー $username の正式パスワードを設定します..."
  
  aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username $username \
    --password $PERMANENT_PASSWORD \
    --permanent
  
  echo "ユーザー $username の正式パスワードを設定しました"
done

echo "すべてのユーザー作成と正式パスワード設定が完了しました"