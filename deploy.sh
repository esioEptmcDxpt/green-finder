# green-finder-dev で実行する
cd app
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com
docker-compose up --build -d
docker tag green-finder:latest 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/green-finder:latest
docker push 326497581172.dkr.ecr.ap-northeast-1.amazonaws.com/green-finder:latest
aws ecs update-service --cluster green-finder --service green-finder --force-new-deployment
cd ..