# Minimal AWS Deployment for POC - $13/month

## 💰 Cost Comparison

| Service | Full Setup | Minimal POC | Savings |
|---------|-----------|-------------|---------|
| ECS Fargate | $30/month | $9/month (Spot) | $21 |
| Application Load Balancer | $20/month | $0 (No ALB) | $20 |
| RDS PostgreSQL | FREE* → $15 | FREE* → $15 | $0 |
| Secrets Manager | $2/month | $0 (Env vars) | $2 |
| ECR | $1/month | $1/month | $0 |
| CloudWatch | $3/month | $3/month | $0 |
| **TOTAL** | **$71/month** | **$13/month** | **$58** |

*FREE for first 12 months with AWS free tier

## 🎯 What's Different in Minimal Setup?

### ❌ Removed:
1. **Application Load Balancer ($20/month)**
   - API accessed directly via public IP
   - IP will change if task restarts (acceptable for POC)
   - No HTTPS (use ALB for production)

2. **Secrets Manager ($2/month)**
   - Database credentials stored as environment variables in task definition
   - Still encrypted at rest by AWS
   - Not recommended for production, but fine for POC

### ✅ Changed:
1. **Fargate Spot instead of standard Fargate**
   - 70% cheaper ($9 vs $30/month)
   - May be interrupted rarely (AWS reclaims capacity)
   - Auto-restarts if interrupted
   - Perfect for non-critical POCs

## 🚀 Quick Start (15 minutes)

### Prerequisites
Same as full setup:
1. AWS account created
2. AWS CLI installed
3. Docker installed
4. PowerShell (Windows)

### Step 1: Run Infrastructure Setup
```powershell
.\setup-minimal-aws.ps1 -DatabasePassword "YourSecurePassword123!" -OpenAIApiKey "sk-proj-..."
```

This creates:
- ✅ ECR repository
- ✅ RDS PostgreSQL (FREE tier)
- ✅ ECS Fargate Spot cluster
- ✅ Security groups (minimal)
- ✅ No ALB, no Secrets Manager

Wait 10-15 minutes for RDS to be ready.

### Step 2: Deploy Application
```powershell
.\deploy-minimal.ps1
```

This will:
1. Build Docker image
2. Push to ECR
3. Register task definition with env vars
4. Deploy to ECS with public IP
5. Show you the public IP address

### Step 3: Test
```bash
# Your API will be at:
http://YOUR_PUBLIC_IP:8000

# Test endpoints:
curl http://YOUR_PUBLIC_IP:8000/health
curl http://YOUR_PUBLIC_IP:8000/docs
```

## ⚠️ Limitations of Minimal Setup

### Acceptable for POC:
- ✅ IP address changes when task restarts
- ✅ No HTTPS (HTTP only)
- ✅ Single task instance (no high availability)
- ✅ Credentials in task definition (encrypted at rest)
- ✅ Fargate Spot interruptions (rare, auto-recovers)

### NOT Recommended for Production:
- ❌ No load balancing
- ❌ No TLS/SSL encryption
- ❌ No auto-scaling
- ❌ Secrets not in Secrets Manager
- ❌ No custom domain

## 🔄 Upgrading to Production Later

When ready to scale, run the full setup:

```powershell
# Switch to full production setup
.\setup-aws-infrastructure.ps1 -DatabasePassword "..." -OpenAIApiKey "sk-proj-..."
.\deploy-to-aws.ps1 -AwsAccountId YOUR_ACCOUNT_ID
```

This adds:
- Application Load Balancer (static DNS)
- Secrets Manager (better security)
- Standard Fargate (no interruptions)
- HTTPS support (with certificate)
- Auto-scaling capabilities

**Cost increase: $13 → $71/month**

## 📊 Monitoring

### View Logs
```powershell
aws logs tail /ecs/rag-knowledge-base --follow --region us-east-1
```

### Check Task Status
```powershell
aws ecs describe-services --cluster rag-kb-cluster --services rag-kb-service
```

### Get Current Public IP
```powershell
# Get task ARN
$taskArn = aws ecs list-tasks --cluster rag-kb-cluster --service-name rag-kb-service --query 'taskArns[0]' --output text

# Get ENI
$eniId = aws ecs describe-tasks --cluster rag-kb-cluster --tasks $taskArn --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text

# Get IP
aws ec2 describe-network-interfaces --network-interface-ids $eniId --query 'NetworkInterfaces[0].Association.PublicIp' --output text
```

## 🧹 Cleanup (Stop Costs)

### Stop Service (keep infrastructure)
```powershell
aws ecs update-service --cluster rag-kb-cluster --service rag-kb-service --desired-count 0
```

### Delete Everything
```powershell
# Delete ECS service
aws ecs delete-service --cluster rag-kb-cluster --service rag-kb-service --force

# Delete ECS cluster
aws ecs delete-cluster --cluster rag-kb-cluster

# Delete RDS (wait ~10 min)
aws rds delete-db-instance --db-instance-identifier rag-kb-postgres --skip-final-snapshot

# Delete ECR images
aws ecr batch-delete-image --repository-name rag-knowledge-base --image-ids imageTag=latest

# Delete ECR repository
aws ecr delete-repository --repository-name rag-knowledge-base

# Delete security groups (after RDS is deleted)
aws ec2 delete-security-group --group-id sg-XXXXX  # ECS SG
aws ec2 delete-security-group --group-id sg-XXXXX  # RDS SG
```

## 🤔 When to Use Minimal vs Full Setup?

### Use Minimal ($13/month) if:
- ✅ POC/testing/development
- ✅ Low traffic (<100 requests/day)
- ✅ Can tolerate occasional downtime
- ✅ Don't need HTTPS
- ✅ Single user/team access
- ✅ Budget-conscious

### Use Full ($71/month) if:
- ✅ Production workload
- ✅ Need HTTPS/SSL
- ✅ Need custom domain
- ✅ Need high availability (99.9%+ uptime)
- ✅ Multiple users/clients
- ✅ Need auto-scaling
- ✅ Security compliance requirements

## 📝 Architecture

```
Internet
   │
   ▼
[ECS Fargate Task with Public IP]
   │         │
   │         └─→ [RDS PostgreSQL]
   │
   └─→ Environment Variables:
         - DATABASE_URL (hardcoded)
         - OPENAI_API_KEY (hardcoded)
```

### Security Notes:
- Environment variables are **encrypted at rest** in ECS
- RDS has **no public access** (only from ECS)
- Security groups restrict traffic
- For better security, upgrade to Secrets Manager

## ❓ FAQ

**Q: Will my IP change?**  
A: Yes, if the ECS task restarts. Use the monitoring commands to get the new IP.

**Q: Is this secure enough?**  
A: For POC, yes. For production, use the full setup with Secrets Manager and ALB.

**Q: What happens if Fargate Spot is interrupted?**  
A: ECS automatically restarts the task. Downtime is typically < 1 minute.

**Q: Can I use a domain name?**  
A: Not easily without ALB. You'd need to manually update DNS each time IP changes.

**Q: How do I scale to 2+ tasks?**  
A: Upgrade to full setup with ALB. Multiple tasks need load balancing.

## 🎯 Summary

**Minimal POC Setup:**
- **Cost:** $13/month (82% savings)
- **Setup Time:** 15 minutes
- **Perfect for:** Testing, development, demos
- **Trade-offs:** No HTTPS, dynamic IP, single instance

**When you're ready for production, upgrade with 2 commands!**
