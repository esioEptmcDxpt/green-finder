# app ディレクトリでコンテナをビルドして ECR にプッシュする
# (参考)このスクリプトに実行権限を付与する場合は、予め chmod +x ecr-push.sh を実行しておく
cd app
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com
# 既存のコンテナがあれば一度削除
# docker-compose down
# プラットフォームを明示的に指定してビルド（重要な変更点）
docker buildx build --platform linux/amd64 -t esio-cis:latest .
# イメージをタグ付け
docker tag esio-cis:latest 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/esio-cis:latest
docker push 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/esio-cis:latest
# 強制的にデプロイ
aws ecs update-service --cluster esio-cis-dev --service esio-cis --force-new-deployment
# 元のディレクトリに戻る
cd ..