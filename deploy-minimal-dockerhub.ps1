# Deploy RAG KB to AWS using Docker Hub image - No ECR needed

param(
    [Parameter(Mandatory=$true)]
    [string]$DockerHubImage,  # e.g., "yourusername/rag-knowledge-base:latest"
    
    [string]$Region = "us-east-1"
)

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "RAG KB - Deploy from Docker Hub" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Load configuration from setup script
if (-not (Test-Path "aws-config.json")) {
    Write-Host "❌ Configuration file not found!" -ForegroundColor Red
    Write-Host "   Please run .\setup-minimal-aws-dockerhub.ps1 first" -ForegroundColor Yellow
    exit 1
}

$config = Get-Content "aws-config.json" | ConvertFrom-Json
$AwsAccountId = $config.AwsAccountId
$Region = $config.Region
$DatabaseUrl = "postgresql://postgres:$($config.DatabasePassword)@$($config.DatabaseEndpoint):5432/rag_kb"
$OpenAIApiKey = $config.OpenAIApiKey
$SubnetIds = $config.SubnetIds
$EcsSecurityGroup = $config.EcsSecurityGroup

Write-Host "🔧 Configuration loaded" -ForegroundColor Green
Write-Host "🐳 Docker Hub Image: $DockerHubImage" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create Task Definition
Write-Host "[1/3] Creating ECS task definition..." -ForegroundColor Yellow

$taskDef = @{
    family = "rag-knowledge-base"
    networkMode = "awsvpc"
    requiresCompatibilities = @("FARGATE")
    cpu = "512"
    memory = "2048"
    executionRoleArn = "arn:aws:iam::${AwsAccountId}:role/ecsTaskExecutionRole"
    containerDefinitions = @(
        @{
            name = "rag-api"
            image = $DockerHubImage
            essential = $true
            portMappings = @(
                @{
                    containerPort = 8000
                    protocol = "tcp"
                }
            )
            environment = @(
                @{
                    name = "DATABASE_URL"
                    value = $DatabaseUrl
                },
                @{
                    name = "OPENAI_API_KEY"
                    value = $OpenAIApiKey
                }
            )
            logConfiguration = @{
                logDriver = "awslogs"
                options = @{
                    "awslogs-group" = "/ecs/rag-knowledge-base"
                    "awslogs-region" = $Region
                    "awslogs-stream-prefix" = "ecs"
                }
            }
            healthCheck = @{
                command = @("CMD-SHELL", "curl -f http://localhost:8000/health || exit 1")
                interval = 30
                timeout = 5
                retries = 3
                startPeriod = 60
            }
        }
    )
} | ConvertTo-Json -Depth 10

$taskDef | Out-File -FilePath "$env:TEMP\task-definition.json" -Encoding utf8

aws ecs register-task-definition `
    --cli-input-json "file://$env:TEMP/task-definition.json" `
    --region $Region | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Task definition registered with Docker Hub image" -ForegroundColor Green
} else {
    Write-Host "  ✗ Failed to register task definition" -ForegroundColor Red
    exit 1
}

# Step 2: Create or Update ECS Service
Write-Host "[2/3] Deploying ECS service..." -ForegroundColor Yellow

$serviceExists = aws ecs describe-services `
    --cluster rag-kb-cluster `
    --services rag-kb-service `
    --region $Region `
    --query 'services[0].status' --output text 2>$null

if ($serviceExists -eq "ACTIVE") {
    # Update existing service
    aws ecs update-service `
        --cluster rag-kb-cluster `
        --service rag-kb-service `
        --task-definition rag-knowledge-base `
        --force-new-deployment `
        --region $Region | Out-Null
    Write-Host "  ✓ Service updated (rolling deployment)" -ForegroundColor Green
} else {
    # Create new service
    aws ecs create-service `
        --cluster rag-kb-cluster `
        --service-name rag-kb-service `
        --task-definition rag-knowledge-base `
        --desired-count 1 `
        --launch-type FARGATE `
        --platform-version LATEST `
        --network-configuration "awsvpcConfiguration={subnets=[$($SubnetIds -join ',')],securityGroups=[$EcsSecurityGroup],assignPublicIp=ENABLED}" `
        --region $Region | Out-Null
    Write-Host "  ✓ Service created with public IP" -ForegroundColor Green
}

# Step 3: Wait for Deployment and Get Public IP
Write-Host "[3/3] Waiting for deployment (pulling from Docker Hub)..." -ForegroundColor Yellow
aws ecs wait services-stable --cluster rag-kb-cluster --services rag-kb-service --region $Region

# Get task ARN
$taskArn = aws ecs list-tasks `
    --cluster rag-kb-cluster `
    --service-name rag-kb-service `
    --region $Region `
    --query 'taskArns[0]' --output text

if ([string]::IsNullOrEmpty($taskArn)) {
    Write-Host "  ✗ No task found. Check ECS console for errors." -ForegroundColor Red
    exit 1
}

# Get ENI ID from task
$eniId = aws ecs describe-tasks `
    --cluster rag-kb-cluster `
    --tasks $taskArn `
    --region $Region `
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text

# Get public IP from ENI
$publicIp = aws ec2 describe-network-interfaces `
    --network-interface-ids $eniId `
    --region $Region `
    --query 'NetworkInterfaces[0].Association.PublicIp' --output text

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🌐 Your API is now available at:" -ForegroundColor Yellow
Write-Host "   http://${publicIp}:8000" -ForegroundColor White
Write-Host ""
Write-Host "📝 Test endpoints:" -ForegroundColor Yellow
Write-Host "   Health: http://${publicIp}:8000/health" -ForegroundColor White
Write-Host "   Docs: http://${publicIp}:8000/docs" -ForegroundColor White
Write-Host "   Collections: http://${publicIp}:8000/api/collections" -ForegroundColor White
Write-Host ""
Write-Host "💰 Cost: ~$12/month" -ForegroundColor Green
Write-Host "   • Fargate Spot: $9/month" -ForegroundColor Gray
Write-Host "   • RDS PostgreSQL: FREE (first year)" -ForegroundColor Gray
Write-Host "   • CloudWatch Logs: $3/month" -ForegroundColor Gray
Write-Host "   • Docker Hub: FREE (public image)" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  Important Notes:" -ForegroundColor Yellow
Write-Host "   • This IP will change if the task restarts" -ForegroundColor Gray
Write-Host "   • No HTTPS (use ALB for production)" -ForegroundColor Gray
Write-Host "   • Image pulled from Docker Hub (public)" -ForegroundColor Gray
Write-Host ""
Write-Host "📊 Monitoring:" -ForegroundColor Yellow
Write-Host "   View logs: aws logs tail /ecs/rag-knowledge-base --follow --region $Region" -ForegroundColor White
Write-Host ""
Write-Host "🔄 To update:" -ForegroundColor Yellow
Write-Host "   1. Push new image to Docker Hub" -ForegroundColor White
Write-Host "   2. Run: .\deploy-minimal-dockerhub.ps1 -DockerHubImage '$DockerHubImage'" -ForegroundColor White
Write-Host ""
