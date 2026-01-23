# 🚀 AWS Deployment - Complete Package

## 💰 Choose Your Deployment

### Option 1: Minimal POC ($13/month) ⭐ RECOMMENDED FOR TESTING
Perfect for proof-of-concept, development, and testing.

**What you get:**
- ✅ Fully functional API
- ✅ 82% cost savings vs full setup
- ✅ 15-minute setup
- ⚠️ Dynamic IP (changes on restart)
- ⚠️ No HTTPS

**See:** [AWS_MINIMAL_POC.md](AWS_MINIMAL_POC.md)

### Option 2: Production Setup ($71/month)
Full production-ready infrastructure with high availability.

**What you get:**
- ✅ Static DNS endpoint
- ✅ HTTPS/SSL encryption
- ✅ Load balancing
- ✅ Secrets Manager
- ✅ Auto-scaling ready

**See guides below**

---

## Files Created for You

### 📁 Main Documentation
1. **AWS_MINIMAL_POC.md** - ⭐ Start here for POC! ($13/month)
2. **AWS_QUICKSTART.md** - Full production setup ($71/month)
3. **AWS_DEPLOYMENT_GUIDE.md** - Detailed step-by-step instructions
4. **README_AWS.md** - This file

### 🛠️ Automation Scripts

**For Minimal POC ($13/month):**
- **setup-minimal-aws.ps1** - Creates minimal infrastructure
- **deploy-minimal.ps1** - Deploys application

**For Production ($71/month):**
- **setup-aws-infrastructure.ps1** - Creates full infrastructure
- **deploy-to-aws.ps1** - Deploys application
- **deploy-to-aws.sh** - Linux/Mac deployment script

### ⚙️ Configuration Files
- **aws/ecs-task-definition.json** - ECS container configuration (for production)

### 📝 Code Changes Made
- **app/core/config.py** - Added AWS-specific settings

---

## Quick Start - Minimal POC (15 Minutes Total)

### Prerequisites (5 min):
```powershell
# 1. Create AWS account at https://aws.amazon.com
# 2. Install AWS CLI: https://awscli.amazonaws.com/AWSCLIV2.msi
# 3. Configure AWS CLI:
aws configure
# Enter: Access Key, Secret Key, us-east-1, json
```

### Step 1: Create Infrastructure (10 min)
```powershell
.\setup-minimal-aws.ps1 -DatabasePassword "YourSecurePassword123!" -OpenAIApiKey "sk-proj-..."
```

### Step 2: Deploy Application (5 min)
```powershell
.\deploy-minimal.ps1
```

**Done!** Your API is now live at `http://YOUR_PUBLIC_IP:8000`

**See [AWS_MINIMAL_POC.md](AWS_MINIMAL_POC.md) for complete guide.**

---

## Full Production Setup (30 Minutes Total)powershell
# 1. Create AWS account at https://aws.amazon.com
# 2. Install AWS CLI: https://awscli.amazonaws.com/AWSCLIV2.msi
# 3. Configure AWS CLI:
aws configure
# Enter your Access Key ID and Secret (from IAM user creation)
```

### One-Command Setup (20 min):
```powershell
# Run this to set up ALL infrastructure automatically:
.\setup-aws-infrastructure.ps1 `
    -DatabasePassword "YourStrongPassword123!" `
    -OpenAIApiKey "sk-proj-your-openai-key"

# This creates:
# ✅ Docker image registry (ECR)
# ✅ PostgreSQL database with pgvector (RDS)
# ✅ Secure secrets storage (Secrets Manager)
# ✅ Load balancer (ALB)
# ✅ Container cluster (ECS Fargate)
# ✅ All networking (VPC, Security Groups)
```

### Deploy Application (5 min):
```powershell
# Get your AWS account ID:
$ACCOUNT_ID = aws sts get-caller-identity --query Account --output text

# Deploy:
.\deploy-to-aws.ps1 -AwsAccountId $ACCOUNT_ID

# Get your API URL:
$URL = aws elbv2 describe-load-balancers --names rag-kb-alb --query 'LoadBalancers[0].DNSName' --output text
Write-Host "Your API: http://$URL/health"
```

---

## What AWS Services You're Using

| Service | Purpose | Cost/Month |
|---------|---------|------------|
| **ECS Fargate** | Run containers serverless | $30 |
| **RDS PostgreSQL** | Managed database | $15 (FREE first year) |
| **ECR** | Store Docker images | $1 |
| **ALB** | Load balancer | $20 |
| **Secrets Manager** | Secure credentials | $2 |
| **CloudWatch** | Logs & monitoring | $3 |
| **Total** | | **$71/month** |

💡 First year with free tier: ~$56/month

---

## Architecture Diagram

```
Internet
   ↓
Application Load Balancer (ALB)
   ↓
ECS Fargate Tasks (Your FastAPI App)
   ↓                    ↓
RDS PostgreSQL    AWS Secrets Manager
(pgvector)        (Environment Variables)
```

---

## What Happens When You Deploy

### Infrastructure Setup (One-time):
1. Creates Docker registry in AWS ECR
2. Spins up PostgreSQL 16 with pgvector extension
3. Stores DATABASE_URL and OPENAI_API_KEY securely
4. Sets up load balancer with health checks
5. Creates serverless container cluster
6. Configures security groups (firewall rules)

### Application Deployment (Ongoing):
1. Builds your Docker image locally
2. Pushes to AWS ECR
3. ECS pulls new image
4. Runs database migrations automatically
5. Starts container(s) with zero downtime
6. Routes traffic through load balancer

---

## Secrets Management (100% Secure)

### ❌ Never Do This:
```python
# DON'T hard-code secrets
DATABASE_URL = "postgresql://postgres:password@..."
OPENAI_API_KEY = "sk-proj-..."
```

### ✅ How It Works in AWS:
```python
# Your code reads from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# AWS injects these from Secrets Manager at runtime
# Secrets never appear in code or Docker images
```

### Stored Secrets:
```powershell
# View stored secrets (values are encrypted)
aws secretsmanager list-secrets

# Secrets:
# 1. rag-kb/database-url (PostgreSQL connection)
# 2. rag-kb/openai-key (OpenAI API key)
```

### Update Secrets:
```powershell
# Change database password
aws secretsmanager update-secret `
    --secret-id rag-kb/database-url `
    --secret-string "postgresql+psycopg://postgres:NEW_PASSWORD@..."

# Update OpenAI key
aws secretsmanager update-secret `
    --secret-id rag-kb/openai-key `
    --secret-string "sk-proj-new-key"

# Restart service to use new secrets
aws ecs update-service `
    --cluster rag-kb-cluster `
    --service rag-kb-service `
    --force-new-deployment
```

---

## Code Changes Required (Already Done!)

### Modified Files:

#### 1. app/core/config.py
```python
# Added AWS-specific configuration
aws_region: str = os.getenv("AWS_REGION", "us-east-1")
aws_s3_bucket: str = os.getenv("AWS_S3_BUCKET", "")
is_production: bool = os.getenv("ENVIRONMENT") == "production"
```

#### 2. aws/ecs-task-definition.json
```json
{
  "secrets": [
    {
      "name": "DATABASE_URL",
      "valueFrom": "arn:aws:secretsmanager:..."
    },
    {
      "name": "OPENAI_API_KEY",
      "valueFrom": "arn:aws:secretsmanager:..."
    }
  ]
}
```

### No Changes Needed:
- ✅ Dockerfile already optimized
- ✅ docker-compose.yml (only for local dev)
- ✅ Database migrations run automatically
- ✅ Health check endpoint exists (/health)

---

## Monitoring & Logs

### View Real-Time Logs:
```powershell
# Tail application logs
aws logs tail /ecs/rag-knowledge-base --follow

# View last hour
aws logs tail /ecs/rag-knowledge-base --since 1h

# Search for errors
aws logs tail /ecs/rag-knowledge-base --filter-pattern "ERROR"
```

### Check Service Health:
```powershell
# Service status
aws ecs describe-services --cluster rag-kb-cluster --services rag-kb-service

# Running tasks
aws ecs list-tasks --cluster rag-kb-cluster

# Health check endpoint
curl http://YOUR_ALB_URL/health
```

### CloudWatch Dashboard:
```
AWS Console → CloudWatch → Dashboards
- CPU/Memory usage
- Request count
- Error rates
- Response times
```

---

## Scaling & Performance

### Auto-Scaling (Optional):
```powershell
# Scale based on CPU (auto-scale from 1 to 5 containers)
aws application-autoscaling register-scalable-target `
    --service-namespace ecs `
    --resource-id service/rag-kb-cluster/rag-kb-service `
    --scalable-dimension ecs:service:DesiredCount `
    --min-capacity 1 `
    --max-capacity 5

# Scale up when CPU > 70%
aws application-autoscaling put-scaling-policy `
    --policy-name cpu-scaling-policy `
    --service-namespace ecs `
    --resource-id service/rag-kb-cluster/rag-kb-service `
    --scalable-dimension ecs:service:DesiredCount `
    --policy-type TargetTrackingScaling `
    --target-tracking-scaling-policy-configuration '{
        "TargetValue": 70.0,
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
        }
    }'
```

### Manual Scaling:
```powershell
# Scale to 3 containers
aws ecs update-service `
    --cluster rag-kb-cluster `
    --service rag-kb-service `
    --desired-count 3
```

---

## Common Operations

### Deploy New Version:
```powershell
# Just run this after code changes:
.\deploy-to-aws.ps1 -AwsAccountId YOUR_ACCOUNT_ID
```

### Rollback to Previous Version:
```powershell
# List previous task definitions
aws ecs list-task-definitions --family-prefix rag-kb-task

# Update service to previous version
aws ecs update-service `
    --cluster rag-kb-cluster `
    --service rag-kb-service `
    --task-definition rag-kb-task:1  # Use previous version number
```

### Connect to Database:
```powershell
# Get DB endpoint
$DB_ENDPOINT = aws rds describe-db-instances `
    --db-instance-identifier rag-kb-postgres `
    --query 'DBInstances[0].Endpoint.Address' --output text

# Connect via SSH tunnel through ECS task (advanced)
# Or enable temporary public access for maintenance
```

### View Costs:
```
AWS Console → Cost Explorer
- See daily/monthly breakdown
- Filter by service
- Set budget alerts
```

---

## Cleanup (Delete Everything)

```powershell
# Delete ECS service
aws ecs delete-service --cluster rag-kb-cluster --service rag-kb-service --force

# Wait for service deletion
Start-Sleep -Seconds 30

# Delete ECS cluster
aws ecs delete-cluster --cluster rag-kb-cluster

# Delete RDS (WARNING: Permanent data loss!)
aws rds delete-db-instance --db-instance-identifier rag-kb-postgres --skip-final-snapshot

# Delete ALB
$ALB_ARN = aws elbv2 describe-load-balancers --names rag-kb-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# Delete target group
$TG_ARN = aws elbv2 describe-target-groups --names rag-kb-targets --query 'TargetGroups[0].TargetGroupArn' --output text
aws elbv2 delete-target-group --target-group-arn $TG_ARN

# Delete ECR repository
aws ecr delete-repository --repository-name rag-knowledge-base --force

# Delete secrets
aws secretsmanager delete-secret --secret-id rag-kb/database-url --force-delete-without-recovery
aws secretsmanager delete-secret --secret-id rag-kb/openai-key --force-delete-without-recovery

# Delete security groups (do this last)
# AWS Console → VPC → Security Groups → Delete rag-kb-* groups
```

---

## Troubleshooting

### Issue: Service won't start
```powershell
# Check task events
aws ecs describe-services --cluster rag-kb-cluster --services rag-kb-service

# Check container logs
aws logs tail /ecs/rag-knowledge-base --follow
```

### Issue: Database connection failed
```powershell
# Verify secret is correct
aws secretsmanager get-secret-value --secret-id rag-kb/database-url

# Check RDS is running
aws rds describe-db-instances --db-instance-identifier rag-kb-postgres

# Verify security groups allow traffic
aws ec2 describe-security-groups --group-ids sg-xxxxx
```

### Issue: Container keeps restarting
```powershell
# Check health check endpoint
curl http://YOUR_ALB_URL/health

# Increase health check grace period
aws ecs update-service `
    --cluster rag-kb-cluster `
    --service rag-kb-service `
    --health-check-grace-period-seconds 300
```

---

## Security Best Practices

### ✅ Already Implemented:
- [x] Secrets in AWS Secrets Manager
- [x] Private subnets for database
- [x] Security groups restrict traffic
- [x] IAM roles for least privilege
- [x] Encrypted storage (RDS & Secrets)

### 🔒 Recommended Additions:
```powershell
# 1. Enable AWS GuardDuty (threat detection)
aws guardduty create-detector --enable

# 2. Enable VPC Flow Logs
aws ec2 create-flow-logs `
    --resource-type VPC `
    --resource-ids $VPC_ID `
    --traffic-type ALL `
    --log-destination-type cloud-watch-logs `
    --log-group-name /aws/vpc/flow-logs

# 3. Set up budget alerts
aws budgets create-budget `
    --account-id $ACCOUNT_ID `
    --budget file://budget.json
```

---

## Support & Next Steps

### 📚 Documentation:
- AWS_QUICKSTART.md - Quick deployment guide
- AWS_DEPLOYMENT_GUIDE.md - Detailed instructions

### 🆘 Get Help:
- AWS Support: https://console.aws.amazon.com/support/
- AWS Forums: https://forums.aws.amazon.com/
- Stack Overflow: Tag with `amazon-ecs`, `aws-fargate`

### 🚀 Production Checklist:
- [ ] Set up custom domain with Route 53
- [ ] Add SSL certificate (free with ACM)
- [ ] Configure auto-scaling
- [ ] Set up automated backups
- [ ] Enable CloudWatch alarms
- [ ] Implement CI/CD with GitHub Actions
- [ ] Add WAF for security
- [ ] Set up staging environment

---

## Cost Optimization Tips

1. **Use Fargate Spot** - 70% cheaper for non-critical workloads
2. **Enable RDS Auto-pause** - Pause during idle hours
3. **Set CloudWatch log retention** - 7 days instead of forever
4. **Delete old ECR images** - Keep only last 10 versions
5. **Use Reserved Instances** - For predictable workloads
6. **Monitor with Cost Explorer** - Set budget alerts

---

**Ready to deploy? Start with AWS_QUICKSTART.md! 🚀**
