# Minimal AWS Setup for POC with Docker Hub - $12/month
# This script creates a cost-optimized deployment without ECR, ALB and Secrets Manager

param(
    [Parameter(Mandatory=$true)]
    [string]$DatabasePassword,
    
    [Parameter(Mandatory=$true)]
    [string]$OpenAIApiKey,
    
    [string]$Region = "us-east-1",
    [string]$ProjectName = "rag-kb"
)

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "RAG KB - Minimal AWS Setup (POC - $12/month)" -ForegroundColor Cyan
Write-Host "Using Docker Hub (No ECR)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Get AWS Account ID
$AwsAccountId = aws sts get-caller-identity --query Account --output text
Write-Host "✓ AWS Account ID: $AwsAccountId" -ForegroundColor Green
Write-Host "✓ Region: $Region" -ForegroundColor Green
Write-Host ""

# Step 1: Get Default VPC
Write-Host "[1/4] Getting VPC information..." -ForegroundColor Yellow
$VpcId = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text --region $Region
Write-Host "  ✓ Using VPC: $VpcId" -ForegroundColor Green

# Get subnets
$SubnetIds = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VpcId" --query 'Subnets[*].SubnetId' --output text --region $Region
$SubnetArray = $SubnetIds -split '\s+'
Write-Host "  ✓ Found $($SubnetArray.Count) subnets" -ForegroundColor Green

# Step 2: Create Security Groups
Write-Host "[2/4] Creating Security Groups..." -ForegroundColor Yellow

# ECS Security Group (allows public access on port 8000)
try {
    $ecsSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=${ProjectName}-ecs-sg" "Name=vpc-id,Values=$VpcId" `
        --query 'SecurityGroups[0].GroupId' --output text --region $Region 2>$null
    
    if ($ecsSgId -eq "None" -or [string]::IsNullOrEmpty($ecsSgId)) {
        $ecsSgId = aws ec2 create-security-group `
            --group-name "${ProjectName}-ecs-sg" `
            --description "Security group for RAG KB ECS tasks" `
            --vpc-id $VpcId `
            --region $Region `
            --query 'GroupId' --output text
        
        # Allow HTTP traffic from anywhere on port 8000
        aws ec2 authorize-security-group-ingress `
            --group-id $ecsSgId `
            --protocol tcp `
            --port 8000 `
            --cidr 0.0.0.0/0 `
            --region $Region | Out-Null
        
        Write-Host "  ✓ Created ECS security group: $ecsSgId" -ForegroundColor Green
    } else {
        Write-Host "  ℹ ECS security group already exists: $ecsSgId" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ✗ Failed to create ECS security group" -ForegroundColor Red
    exit 1
}

# RDS Security Group
try {
    $rdsSgId = aws ec2 describe-security-groups `
        --filters "Name=group-name,Values=${ProjectName}-rds-sg" "Name=vpc-id,Values=$VpcId" `
        --query 'SecurityGroups[0].GroupId' --output text --region $Region 2>$null
    
    if ($rdsSgId -eq "None" -or [string]::IsNullOrEmpty($rdsSgId)) {
        $rdsSgId = aws ec2 create-security-group `
            --group-name "${ProjectName}-rds-sg" `
            --description "Security group for RAG KB RDS" `
            --vpc-id $VpcId `
            --region $Region `
            --query 'GroupId' --output text
        
        # Allow PostgreSQL from ECS
        aws ec2 authorize-security-group-ingress `
            --group-id $rdsSgId `
            --protocol tcp `
            --port 5432 `
            --source-group $ecsSgId `
            --region $Region | Out-Null
        
        Write-Host "  ✓ Created RDS security group: $rdsSgId" -ForegroundColor Green
    } else {
        Write-Host "  ℹ RDS security group already exists: $rdsSgId" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ✗ Failed to create RDS security group" -ForegroundColor Red
    exit 1
}

# Step 3: Create RDS PostgreSQL Instance
Write-Host "[3/4] Creating RDS PostgreSQL (FREE tier, takes 10-15 min)..." -ForegroundColor Yellow
try {
    $dbInstance = aws rds describe-db-instances --db-instance-identifier "${ProjectName}-postgres" --region $Region 2>$null
    if ($dbInstance) {
        Write-Host "  ℹ RDS instance already exists" -ForegroundColor Gray
        $dbEndpoint = aws rds describe-db-instances `
            --db-instance-identifier "${ProjectName}-postgres" `
            --query 'DBInstances[0].Endpoint.Address' `
            --output text --region $Region
    } else {
        # Create DB subnet group first
        try {
            aws rds create-db-subnet-group `
                --db-subnet-group-name "${ProjectName}-db-subnet" `
                --db-subnet-group-description "Subnet group for RAG KB database" `
                --subnet-ids $SubnetArray `
                --region $Region 2>$null | Out-Null
        } catch {
            Write-Host "  ℹ Subnet group may already exist" -ForegroundColor Gray
        }

        aws rds create-db-instance `
            --db-instance-identifier "${ProjectName}-postgres" `
            --db-instance-class db.t3.micro `
            --engine postgres `
            --engine-version 16.1 `
            --master-username postgres `
            --master-user-password $DatabasePassword `
            --allocated-storage 20 `
            --db-name rag_kb `
            --vpc-security-group-ids $rdsSgId `
            --db-subnet-group-name "${ProjectName}-db-subnet" `
            --backup-retention-period 7 `
            --no-publicly-accessible `
            --storage-encrypted `
            --region $Region | Out-Null
        
        Write-Host "  ⏳ Waiting for RDS instance (10-15 minutes)..." -ForegroundColor Yellow
        aws rds wait db-instance-available --db-instance-identifier "${ProjectName}-postgres" --region $Region
        
        $dbEndpoint = aws rds describe-db-instances `
            --db-instance-identifier "${ProjectName}-postgres" `
            --query 'DBInstances[0].Endpoint.Address' `
            --output text --region $Region
        
        Write-Host "  ✓ RDS instance created: $dbEndpoint" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ Failed to create RDS instance" -ForegroundColor Red
    exit 1
}

# Step 4: Create ECS Cluster and IAM Role
Write-Host "[4/4] Creating ECS Cluster..." -ForegroundColor Yellow
try {
    $clusterExists = aws ecs describe-clusters --clusters "${ProjectName}-cluster" --region $Region --query 'clusters[0].status' --output text 2>$null
    if ($clusterExists -eq "ACTIVE") {
        Write-Host "  ℹ ECS cluster already exists" -ForegroundColor Gray
    } else {
        aws ecs create-cluster `
            --cluster-name "${ProjectName}-cluster" `
            --capacity-providers FARGATE_SPOT `
            --default-capacity-provider-strategy "capacityProvider=FARGATE_SPOT,weight=1" `
            --region $Region | Out-Null
        Write-Host "  ✓ Created ECS cluster with Fargate Spot (70% cheaper!)" -ForegroundColor Green
    }
} catch {
    Write-Host "  ℹ ECS cluster may already exist" -ForegroundColor Gray
}

# Create CloudWatch log group
try {
    aws logs create-log-group --log-group-name "/ecs/rag-knowledge-base" --region $Region 2>$null | Out-Null
    Write-Host "  ✓ Created CloudWatch log group" -ForegroundColor Green
} catch {
    Write-Host "  ℹ CloudWatch log group already exists" -ForegroundColor Gray
}

# Create IAM Role
try {
    $roleExists = aws iam get-role --role-name ecsTaskExecutionRole 2>$null
    if (!$roleExists) {
        $trustPolicy = @{
            Version = "2012-10-17"
            Statement = @(
                @{
                    Effect = "Allow"
                    Principal = @{
                        Service = "ecs-tasks.amazonaws.com"
                    }
                    Action = "sts:AssumeRole"
                }
            )
        } | ConvertTo-Json -Depth 10
        
        $trustPolicy | Out-File -FilePath "$env:TEMP\trust-policy.json" -Encoding utf8
        
        aws iam create-role `
            --role-name ecsTaskExecutionRole `
            --assume-role-policy-document "file://$env:TEMP/trust-policy.json" | Out-Null
        
        aws iam attach-role-policy `
            --role-name ecsTaskExecutionRole `
            --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy" | Out-Null
        
        Write-Host "  ✓ Created IAM role" -ForegroundColor Green
    } else {
        Write-Host "  ℹ IAM role already exists" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ℹ IAM role may already exist" -ForegroundColor Gray
}

# Save configuration for deployment script
$config = @{
    AwsAccountId = $AwsAccountId
    Region = $Region
    DatabaseEndpoint = $dbEndpoint
    DatabasePassword = $DatabasePassword
    OpenAIApiKey = $OpenAIApiKey
    EcsSecurityGroup = $ecsSgId
    SubnetIds = $SubnetArray
}

$config | ConvertTo-Json | Out-File -FilePath "aws-config.json" -Encoding utf8

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Infrastructure Setup Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "💰 Cost Savings Summary:" -ForegroundColor Yellow
Write-Host "  • No Load Balancer: -$20/month" -ForegroundColor Green
Write-Host "  • No Secrets Manager: -$2/month" -ForegroundColor Green
Write-Host "  • No ECR (using Docker Hub): -$1/month" -ForegroundColor Green
Write-Host "  • Fargate Spot: -$21/month" -ForegroundColor Green
Write-Host "  • Total Monthly Cost: ~`$12" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Resources Created:" -ForegroundColor Yellow
Write-Host "  • RDS PostgreSQL: $dbEndpoint (FREE first year)" -ForegroundColor White
Write-Host "  • ECS Cluster: ${ProjectName}-cluster (Fargate Spot)" -ForegroundColor White
Write-Host "  • Security Groups: Minimal (ECS + RDS only)" -ForegroundColor White
Write-Host "  • IAM Role: ecsTaskExecutionRole" -ForegroundColor White
Write-Host ""
Write-Host "🚀 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Build and push to Docker Hub:" -ForegroundColor White
Write-Host "     docker build -t yourusername/rag-knowledge-base:latest ." -ForegroundColor Gray
Write-Host "     docker push yourusername/rag-knowledge-base:latest" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Deploy application:" -ForegroundColor White
Write-Host "     .\deploy-minimal-dockerhub.ps1 -DockerHubImage 'yourusername/rag-knowledge-base:latest'" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  Note: Using public Docker Hub (FREE)" -ForegroundColor Yellow
Write-Host "   Make sure your image doesn't contain secrets!" -ForegroundColor Gray
Write-Host ""
