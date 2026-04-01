# Infrastructure (Terraform)

## Resources

### us-east-1 (Platform)
- VPC + public subnet + IGW
- EC2 r6i.2xlarge (100GB gp3) — runs platform code, LiteLLM, Playwright
- S3 bucket (versioning + encryption + public access block) — experiment data
- IAM role: `bedrock:InvokeModel` + S3 CRUD (least privilege)
- Security group: SSH (22) inbound, all outbound

### us-east-2 (WebArena)
- EC2 t3a.xlarge (1TB gp3) — WebArena pre-installed AMI (`ami-08a862bf98e3bd7aa`)
- Security group: SSH (22) + app ports (3000, 7770, 7780, 8023, 8888, 9999)
- Uses default VPC (no custom networking needed)

## Files

| File | Purpose |
|------|---------|
| `main.tf` | Platform instance, VPC, S3, IAM, variables |
| `webarena.tf` | WebArena instance in us-east-2 with ohio provider |
| `outputs.tf` | Platform outputs (IP, S3 bucket, SSH command) |
| `user-data.sh` | Platform bootstrap (Node, Docker, Playwright, Python, LiteLLM) |
| `terraform.tfvars.example` | Sample variable values |

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your SSH key path

terraform init
terraform plan
terraform apply
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | us-east-1 | Platform region (must support Bedrock) |
| `instance_type` | r6i.2xlarge | Platform EC2 type |
| `ssh_public_key_path` | (required) | Path to RSA public key |
| `project_name` | a11y-platform | Resource naming prefix |
| `github_repo` | (repo URL) | Git repo for platform code |

## WebArena App Ports

| App | Port | Docker Container |
|-----|------|-----------------|
| Reddit (Postmill) | 9999 | forum |
| Shopping (Magento) | 7770 | shopping |
| Shopping Admin | 7780 | shopping_admin |
| GitLab | 8023 | gitlab |
| Wikipedia (Kiwix) | 8888 | kiwix33 |
| Map (OpenStreetMap) | 3000 | openstreetmap |

## Cost Estimate (Burner Account)

| Resource | Hourly | Daily |
|----------|--------|-------|
| r6i.2xlarge (platform) | ~$0.50 | ~$12 |
| t3a.xlarge (WebArena) | ~$0.15 | ~$3.60 |
| S3 | negligible | — |
| Bedrock LLM calls | varies | ~$10/pilot |
| **Total** | | **~$25/day** |

Burner account auto-deletes after 7 days.
