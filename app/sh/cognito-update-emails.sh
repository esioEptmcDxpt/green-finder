# メールアドレス更新スクリプト
# (参考)source sh/cognito-update-emails.sh で実行可能
# (参考)このスクリプトに実行権限を付与する場合は、予め chmod +x sh/cognito-update-emails.sh を実行しておく

USER_POOL_ID="ap-northeast-1_OPZscsccQ"  # ユーザープールIDを指定

# ユーザーIDと変更後のメールアドレスのリスト（コンマ区切り）
USERS=(
  "shinagawa,fuga@jreast.co.jp"
  "shinjuku,fuge@jreast.co.jp"
  "ueno,hogera@jreast.co.jp"
  "yokohama,piyo@jreast.co.jp"
  "hachioji,piko@jreast.co.jp"
  "oomiya,fusu@jreast.co.jp"
  "takasaki,teke@jreast.co.jp"
  "mito,hogu@jreast.co.jp"
  "chiba,degu@jreast.co.jp"
  "nagano,suge@jreast.co.jp"
  "sendai,godo@jreast.co.jp"
  "morioka,eutk@jreast.co.jp"
  "akita,cmgj@jreast.co.jp"
  "niigata,wotj@jreast.co.jp"
)

# 全ユーザーのメールアドレスを更新
for user in "${USERS[@]}"; do
  IFS=',' read -r username new_email <<< "$user"
  
  echo "ユーザー $username のメールアドレスを $new_email に更新します..."
  
  # メールアドレスの更新とメール検証ステータスを更新
  aws cognito-idp admin-update-user-attributes \
    --user-pool-id $USER_POOL_ID \
    --username $username \
    --user-attributes Name=email,Value="$new_email" Name=email_verified,Value=true
  
  # 結果の確認
  if [ $? -eq 0 ]; then
    echo "ユーザー $username のメールアドレスを正常に更新しました"
  else
    echo "エラー: ユーザー $username のメールアドレス更新に失敗しました"
  fi
done

echo "すべてのメールアドレス更新が完了しました"