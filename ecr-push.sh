# app ディレクトリでコンテナをビルドして ECR にプッシュする
# (参考)source ecr-push.sh で実行可能
# (参考)このスクリプトに実行権限を付与する場合は、予め chmod +x ecr-push.sh を実行しておく
cd app

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
# 元のディレクトリに戻る
cd ..