import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as ecs_patterns from "aws-cdk-lib/aws-ecs-patterns";

export class EsioCisAppStack extends cdk.Stack {
  public readonly vpc: ec2.IVpc;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // contextからVPC設定を読み込む
    const vpcId = this.node.tryGetContext("vpc").id;
    const vpcName = this.node.tryGetContext("vpc").name;

    // 既存のVPCを読み込む
    this.vpc = ec2.Vpc.fromLookup(this, "ExistingVpc", {
      vpcId: vpcId,
      vpcName: vpcName,
    });

    // ECSクラスターを作成
    const cluster = new ecs.Cluster(this, "BscCluster", {
      vpc: this.vpc,
      clusterName: "esio-cis",
    });

    // ECSタスク用IAMロールの作成
    const taskRole = new iam.Role(this, "BscTaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      roleName: "esio-cis-task-role",
    });
    taskRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonDynamoDBFullAccess")
    );

    // ECRリポジトリの参照
    // ※既存のECRリポジトリ「esio-cis」をインポート
    const repository = ecr.Repository.fromRepositoryName(
      this,
      "BscEcrRepo",
      "esio-cis"
    );

    // Fargate タスク定義の作成
    const taskDefinition = new ecs.FargateTaskDefinition(
      this,
      "EsioCisTaskDef",
      {
        memoryLimitMiB: 1024,
        cpu: 512,
        taskRole: taskRole,
      }
    );

    taskDefinition.addContainer("EsioCisContainer", {
      containerName: "esio-cis",
      image: ecs.ContainerImage.fromEcrRepository(repository, "latest"),
      portMappings: [{ containerPort: 8501 }],
      logging: ecs.LogDriver.awsLogs({ streamPrefix: "esio-cis" }),
    });

    // Fargate サービス＋ALB の作成
    // ecs_patternsのApplicationLoadBalancedFargateServiceを利用してALBとFargateサービスを一括作成
    const fargateService =
      new ecs_patterns.ApplicationLoadBalancedFargateService(
        this,
        "BsioCisFargateService",
        {
          cluster,
          taskDefinition,
          publicLoadBalancer: true,
          listenerPort: 80,
          desiredCount: 1,
          assignPublicIp: true,
          // ヘルスチェック設定を緩和
          healthCheckGracePeriod: cdk.Duration.seconds(120), // 2分間のグレースピリオド
          // スタートアップ中のタスク数を調整
          minHealthyPercent: 0, // デプロイ中に0タスクになることを許可
          maxHealthyPercent: 100,
          // ※ALBはデフォルトのセキュリティグループが付与されるため、後でカスタムSGを追加
        }
      );

    // ターゲットグループのヘルスチェック設定をカスタマイズ
    fargateService.targetGroup.configureHealthCheck({
      path: "/",
      interval: cdk.Duration.seconds(30),
      timeout: cdk.Duration.seconds(10),
      healthyThresholdCount: 2,
      unhealthyThresholdCount: 5,
    });

    // CloudFormation 情報の出力
    new cdk.CfnOutput(this, "VpcId", {
      value: this.vpc.vpcId,
      description: "VPC ID",
      exportName: "EsioCisVpcId",
    });

    // ALB DNS名の出力
    new cdk.CfnOutput(this, "ALB_DNS", {
      value: fargateService.loadBalancer.loadBalancerDnsName,
      description: "DNS name of the Application Load Balancer",
    });
  }
}
