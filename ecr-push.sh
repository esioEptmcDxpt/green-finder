# app ディレクトリでコンテナをビルドして ECR にプッシュする
# (参考)このスクリプトに実行権限を付与する場合は、予め chmod +x ecr-push.sh を実行しておく
cd app
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com
docker-compose build --no-cache
docker tag esio-cis:latest 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/esio-cis:latest
docker push 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/esio-cis:latest
cd ..