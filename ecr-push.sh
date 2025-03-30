# app ディレクトリでコンテナをビルドして ECR にプッシュする
# (参考)source ecr-push.sh で実行可能
# (参考)このスクリプトに実行権限を付与する場合は、予め chmod +x ecr-push.sh を実行しておく
cd app

# secrets.tomlのredirect_uriを確認し、必要に応じて変更する
SECRETS_FILE=".streamlit/secrets.toml"
ORIGINAL_URI=""

if grep -q "redirect_uri = \"http://localhost:8501\"" $SECRETS_FILE; then
  echo "ローカル用のredirect_uriを本番用に変更します"
  ORIGINAL_URI="http://localhost:8501"
  # バックアップを作成
  cp $SECRETS_FILE "${SECRETS_FILE}.bak"
  # redirect_uriを変更
  sed -i '' 's|redirect_uri = "http://localhost:8501"|redirect_uri = "https://esio-cis.com"|g' $SECRETS_FILE
  echo "redirect_uriを変更しました: $ORIGINAL_URI -> https://esio-cis.com"
fi

# ECRにログイン
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com

# (エラーが出る場合用) 既存のコンテナがあれば一度削除
# docker-compose down

# プラットフォームを明示的に指定してビルド（ARM64に変更）
docker buildx build --platform linux/arm64 -t esio-cis:latest .
# イメージをタグ付け
docker tag esio-cis:latest 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/esio-cis:latest
# イメージをECRにプッシュ
docker push 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/esio-cis:latest
# ECSのサービスを強制的にデプロイ
aws ecs update-service --cluster esio-cis-dev --service esio-cis --force-new-deployment

# ECRへのプッシュ後、redirect_uriを元に戻す
if [ ! -z "$ORIGINAL_URI" ]; then
  echo "redirect_uriを元に戻します"
  # バックアップから復元
  mv "${SECRETS_FILE}.bak" $SECRETS_FILE
  echo "redirect_uriを復元しました: https://esio-cis.com -> $ORIGINAL_URI"
fi

# 元のディレクトリに戻る
cd ..