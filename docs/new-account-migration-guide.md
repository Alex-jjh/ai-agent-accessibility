# 新 AWS 账户部署迁移指南

本文档详细列出将 AI Agent Accessibility Platform 完整部署到新 AWS 账户时，所有需要修改的配置项、文件和步骤。

---

## 1. 前置条件

### 1.1 新账户准备

- 获取新的 burner 账户（`https://iad.merlon.amazon.dev/burner-accounts`）
- 账户需要以下权限/服务：
  - EC2（r6i.4xlarge + r6i.2xlarge）
  - S3
  - IAM（创建 role/policy/instance-profile）
  - VPC（创建 VPC/Subnet/NAT/IGW/VPC Endpoints）
  - SSM Session Manager
  - Bedrock Runtime（Claude Sonnet/Opus/Haiku, Nova Pro, Llama 4）
- 安装 AWS CLI v2 + SSM Session Manager Plugin
- 安装 Terraform >= 1.5

### 1.2 Bedrock 模型访问

新账户需要在 Bedrock 控制台中申请以下模型的访问权限（Model Access）：

| 模型 | Bedrock Model ID |
|------|-----------------|
| Claude Opus 4.1 | `us.anthropic.claude-opus-4-1-20250805-v1:0` |
| Claude Sonnet 4 | `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| Claude Haiku 3.5 | `us.anthropic.claude-3-5-haiku-20241022-v1:0` |
| Amazon Nova Pro | `us.amazon.nova-pro-v1:0` |
| Meta Llama 4 | `us.meta.llama4-maverick-17b-instruct-v1:0` |

这些模型使用 geo-inference endpoint（`us.` 前缀），IAM 策略需要同时包含 `foundation-model/*` 和 `inference-profile/*` 资源。

---

## 2. 需要修改的文件清单

### 2.1 Terraform 基础设施

#### `infra/main.tf`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| `provider.aws.profile` | `"a11y-pilot"` | 改为新账户的 AWS CLI profile 名称。如果不使用 profile 而是用环境变量认证，可以删除此行 |
| `variable.aws_region.default` | `"us-east-2"` | **必须保持 `us-east-2`**，因为 WebArena AMI 只在此 region 可用。如果要换 region，需要先将 AMI 复制到目标 region（见 §3.1） |
| `variable.instance_type.default` | `"r6i.4xlarge"` | 可根据预算调整。最低建议 `r6i.xlarge`（4 vCPU, 32GB），实验运行需要大量内存 |
| `variable.github_repo.default` | `"https://github.com/Alex-jjh/ai-agent-accessibility.git"` | 改为你的 repo URL。如果是私有 repo，需要在 user-data.sh 中配置 git 认证 |

#### `infra/webarena.tf`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| `aws_instance.webarena.ami` | `"ami-08a862bf98e3bd7aa"` | WebArena 预装 AMI，**仅在 us-east-2 可用**。换 region 需要先 `aws ec2 copy-image` 到目标 region |
| `aws_instance.webarena.instance_type` | `"r6i.2xlarge"` | 可调整。WebArena Docker 容器（特别是 GitLab）需要至少 4GB RAM |
| `root_block_device.volume_size` | `1000` | WebArena Docker 镜像需要约 800GB。不建议减小 |

#### `infra/terraform.tfvars.example` → 创建 `infra/terraform.tfvars`

```hcl
aws_region    = "us-east-2"           # 保持不变（AMI 限制）
instance_type = "r6i.4xlarge"         # 按需调整
project_name  = "a11y-platform"       # 按需修改，影响所有资源命名
github_repo   = "https://github.com/<YOUR_USER>/<YOUR_REPO>.git"
```

#### `infra/user-data.sh`

此文件通过 Terraform `templatefile()` 注入变量，不需要手动修改。但注意：
- `${github_repo}` — 来自 terraform.tfvars
- `${s3_bucket}` — Terraform 自动生成
- `${aws_region}` — 来自 terraform.tfvars

#### `infra/outputs.tf`

无需修改。输出值由 Terraform 动态生成。

---

### 2.2 AWS 认证配置

#### 本地 AWS CLI Profile

```bash
# 配置新账户凭证
mwinit -o
ada credentials update \
  --account=<NEW_ACCOUNT_ID> \
  --provider=conduit \
  --role=IibsAdminAccess-DO-NOT-DELETE \
  --once \
  --profile=a11y-pilot

# 或者改用其他 profile 名称（需同步修改 infra/main.tf 中的 profile）
```

如果不使用 `ada`（非 Amazon 内部账户），配置 `~/.aws/credentials`：

```ini
[a11y-pilot]
aws_access_key_id = <KEY>
aws_secret_access_key = <SECRET>
# 或使用 SSO
```

---

### 2.3 实验配置文件（WebArena URL）

部署后，WebArena EC2 会获得新的 private IP（通过 `terraform output webarena_private_ip` 查看）。以下所有 YAML 配置文件中的 `10.0.1.49` 需要替换为新 IP：

| 文件 | 需要修改的字段 |
|------|---------------|
| `config.yaml` | `webarena.apps.*.url`（使用 `localhost`，仅本地开发用） |
| `config-pilot.yaml` | `webarena.apps.ecommerce.url`, `ecommerce_admin.url`, `reddit.url` |
| `config-pilot2.yaml` | 同上 |
| `config-pilot3.yaml` | 同上 |
| `config-pilot3b.yaml` | 同上 |
| `config-pilot4.yaml` | `webarena.apps.ecommerce.url`, `ecommerce_admin.url`, `reddit.url` |
| `config-pilot4-cua.yaml` | 同上 |
| `config-regression.yaml` | 同上 |
| `config-reinject-smoke.yaml` | 同上 |
| `config-vision-smoke.yaml` | `webarena.apps.reddit.url` |
| `config-cua-smoke.yaml` | `webarena.apps.shopping.url` |

**快速替换命令**（在 repo 根目录执行）：

```bash
# 获取新 IP
NEW_IP=$(cd infra && terraform output -raw webarena_private_ip)

# 批量替换所有 config 文件
sed -i "s/10\.0\.1\.49/$NEW_IP/g" config*.yaml
```

---

### 2.4 LiteLLM 配置

#### `litellm_config.yaml`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| 所有 `aws_region_name` | `us-east-2` | **必须与 VPC Endpoint 所在 region 一致**。如果 Terraform 部署在 us-east-2，保持不变 |
| Bedrock Model IDs | 见文件 | 如果新账户没有某些模型的访问权限，注释掉对应条目 |

如果换 region，需要同时修改：
1. `litellm_config.yaml` 中所有 `aws_region_name`
2. `infra/main.tf` 中 Bedrock IAM policy 的 Resource ARN
3. `infra/main.tf` 中 VPC Endpoint 的 `service_name`

---

### 2.5 CUA Bridge（直接调用 Bedrock）

#### `src/runner/cua_bridge.py`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| `BEDROCK_MODEL_ID` | `"us.anthropic.claude-sonnet-4-20250514-v1:0"` | 如果使用不同模型，修改此值 |
| `BEDROCK_REGION` | `"us-east-2"` | **必须与 VPC Endpoint region 一致** |

#### `scripts/smoke-cua-bedrock-direct.py`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| `MODEL_ID` | `"us.anthropic.claude-sonnet-4-20250514-v1:0"` | 同上 |
| `REGION` | `"us-east-2"` | 同上 |

---

### 2.6 LLM Backend（TypeScript）

#### `src/runner/backends/llm.ts`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| `LITELLM_BASE_URL` | `"http://localhost:4000/v1/chat/completions"` | 无需修改。LiteLLM 始终在 Platform EC2 本地运行 |

---

### 2.7 S3 同步脚本

#### `scripts/sync-to-s3.sh`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| `REGION` 默认值 | `us-east-2` | 如果换 region 需要修改 |
| Bucket 名称 | 自动检测（`a11y-platform-data-*`） | Terraform 自动创建，脚本自动检测。无需手动修改 |

---

### 2.8 Steering 文件（项目上下文）

#### `.kiro/steering/project-context.md`

| 配置项 | 当前值 | 修改说明 |
|--------|--------|----------|
| Platform EC2 instance ID | `i-0288f77960077b755` | 替换为新的 instance ID（`terraform output instance_id`） |
| WebArena EC2 instance ID | `i-0c916d784df56d796` | 替换为新的 instance ID（`terraform output webarena_instance_id`） |

---

## 3. 部署步骤（按顺序执行）

### 3.1 Region 选择决策

**推荐：保持 `us-east-2`**。原因：
- WebArena AMI (`ami-08a862bf98e3bd7aa`) 仅在 us-east-2 可用
- 所有配置已针对此 region 调试完毕

如果必须换 region：
```bash
# 1. 复制 AMI 到目标 region
aws ec2 copy-image \
  --source-region us-east-2 \
  --source-image-id ami-08a862bf98e3bd7aa \
  --name "webarena-copied" \
  --region <TARGET_REGION>

# 2. 等待 AMI 可用（可能需要 30-60 分钟，因为 1TB 磁盘）
aws ec2 describe-images --image-ids <NEW_AMI_ID> --region <TARGET_REGION>

# 3. 更新 infra/webarena.tf 中的 ami 值
# 4. 更新所有 region 引用（见 §2 中的所有文件）
```

### 3.2 Terraform 部署

```bash
# 1. 配置凭证
export AWS_PROFILE=a11y-pilot  # 或你的 profile 名称
aws sts get-caller-identity    # 确认是新账户

# 2. 创建 tfvars
cd infra
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars（见 §2.1）

# 3. 初始化并部署
terraform init
terraform plan    # 检查资源列表
terraform apply   # 确认后输入 yes

# 4. 记录输出
terraform output
# 记下：
#   instance_id          — Platform EC2
#   webarena_instance_id — WebArena EC2
#   webarena_private_ip  — 用于更新 config YAML
#   s3_bucket_name       — 数据存储
#   ssm_platform         — 连接命令
#   ssm_webarena         — 连接命令
```

**Terraform 创建的资源清单**：

| 资源 | 类型 | 用途 |
|------|------|------|
| VPC | `aws_vpc` | 10.0.0.0/16，隔离网络 |
| Public Subnet | `aws_subnet` | 10.0.0.0/24，仅放 NAT Gateway |
| Private Subnet | `aws_subnet` | 10.0.1.0/24，放两台 EC2 |
| Internet Gateway | `aws_internet_gateway` | Public subnet 出口 |
| NAT Gateway + EIP | `aws_nat_gateway` | Private subnet 出口（yum/git/pip） |
| Security Group | `aws_security_group` | VPC 内 HTTPS + WebArena 端口，无公网入站 |
| VPC Endpoint: SSM | `aws_vpc_endpoint` (Interface) | Session Manager 连接 |
| VPC Endpoint: SSMMessages | `aws_vpc_endpoint` (Interface) | Session Manager 消息 |
| VPC Endpoint: EC2Messages | `aws_vpc_endpoint` (Interface) | SSM Agent 通信 |
| VPC Endpoint: Bedrock | `aws_vpc_endpoint` (Interface) | LLM API 调用 |
| VPC Endpoint: S3 | `aws_vpc_endpoint` (Gateway) | 数据同步（免费） |
| IAM Role: Platform | `aws_iam_role` | SSM + Bedrock + S3 权限 |
| IAM Role: WebArena | `aws_iam_role` | SSM 权限 |
| S3 Bucket | `aws_s3_bucket` | 实验数据存储 |
| EC2: Platform | `aws_instance` | r6i.4xlarge, 100GB, Amazon Linux 2023 |
| EC2: WebArena | `aws_instance` | r6i.2xlarge, 1TB, WebArena AMI (Ubuntu) |

### 3.3 WebArena 配置（SSM 连接到 WebArena EC2）

```bash
# 连接
aws ssm start-session --target <webarena_instance_id> --region us-east-2

# WebArena AMI 的 user-data 会自动启动 Docker 容器并配置 Magento base URL
# 但需要验证：

# 1. 检查 Docker 容器状态
sudo docker ps --format "table {{.Names}}\t{{.Status}}"
# 应该看到: gitlab, shopping, shopping_admin, forum, kiwix33

# 2. 验证 Magento base URL（最关键的一步）
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
echo "Private IP: $PRIVATE_IP"

# 测试 shopping — 应该返回 200，不是 302
curl -v http://$PRIVATE_IP:7770 2>&1 | grep -E "HTTP|Location"
# 如果看到 302 redirect 到错误的 hostname，手动修复：
sudo docker exec shopping /var/www/magento2/bin/magento setup:store-config:set \
  --base-url="http://$PRIVATE_IP:7770/"
sudo docker exec shopping mysql -u magentouser -pMyPassword magentodb \
  -e "UPDATE core_config_data SET value='http://$PRIVATE_IP:7770/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping /var/www/magento2/bin/magento cache:flush

# 同样处理 shopping_admin
sudo docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set \
  --base-url="http://$PRIVATE_IP:7780/"
sudo docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb \
  -e "UPDATE core_config_data SET value='http://$PRIVATE_IP:7780/' WHERE path = 'web/secure/base_url';"
sudo docker exec shopping_admin /var/www/magento2/bin/magento cache:flush

# 3. 验证所有服务
curl -s http://$PRIVATE_IP:7770 | head -5   # Shopping
curl -s http://$PRIVATE_IP:7780 | head -5   # Shopping Admin
curl -s http://$PRIVATE_IP:9999 | head -5   # Reddit
curl -s http://$PRIVATE_IP:8023 | head -5   # GitLab（可能需要等 10-15 分钟）
curl -s http://$PRIVATE_IP:8888 | head -5   # Wikipedia
```

### 3.4 Platform 配置（SSM 连接到 Platform EC2）

```bash
# 连接
aws ssm start-session --target <platform_instance_id> --region us-east-2

# 切换到 ec2-user
sudo su - ec2-user

# 加载 nvm（SSM session 不自动加载 .bashrc）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# 1. 进入项目目录
cd ~/platform

# 2. 如果 user-data 没有自动 clone（检查目录是否存在）
# git clone <YOUR_REPO_URL> ~/platform

# 3. 运行 bootstrap
bash scripts/bootstrap-platform.sh
# 这会安装：Python 3.11, Node.js 20, Playwright, BrowserGym, LiteLLM

# 4. 更新 config 文件中的 WebArena IP
WEBARENA_IP=<webarena_private_ip>  # 从 terraform output 获取
sed -i "s/10\.0\.1\.49/$WEBARENA_IP/g" config*.yaml

# 5. 设置 WebArena 环境变量（BrowserGym 要求全部 7 个）
export WA_SHOPPING="http://$WEBARENA_IP:7770"
export WA_SHOPPING_ADMIN="http://$WEBARENA_IP:7780"
export WA_REDDIT="http://$WEBARENA_IP:9999"
export WA_GITLAB="http://$WEBARENA_IP:8023"
export WA_WIKIPEDIA="http://$WEBARENA_IP:8888"
export WA_MAP="http://$WEBARENA_IP:3000"
export WA_HOMEPAGE="http://$WEBARENA_IP:7770"

# 写入 .bashrc 以便后续 session 自动加载
cat >> ~/.bashrc << EOF
export WA_SHOPPING="http://$WEBARENA_IP:7770"
export WA_SHOPPING_ADMIN="http://$WEBARENA_IP:7780"
export WA_REDDIT="http://$WEBARENA_IP:9999"
export WA_GITLAB="http://$WEBARENA_IP:8023"
export WA_WIKIPEDIA="http://$WEBARENA_IP:8888"
export WA_MAP="http://$WEBARENA_IP:3000"
export WA_HOMEPAGE="http://$WEBARENA_IP:7770"
EOF

# 6. 启动 LiteLLM
~/.local/bin/litellm --config litellm_config.yaml --port 4000 &

# 7. 验证 LiteLLM
curl -s http://localhost:4000/health
curl -s http://localhost:4000/model/info | python -m json.tool | head -20

# 8. 验证 WebArena 连通性（从 Platform EC2 访问 WebArena EC2）
curl -s http://$WEBARENA_IP:7770 | head -5
curl -s http://$WEBARENA_IP:9999 | head -5

# 9. 运行 smoke test
npx tsx scripts/run-pilot3.ts --config config-reinject-smoke.yaml --dry-run
```

### 3.5 验证部署

```bash
# 在 Platform EC2 上运行回归测试
npx tsx scripts/run-pilot3.ts --config config-regression.yaml

# 检查结果
find data/regression -name "trace-attempt-*.json" | wc -l
```

---

## 4. 安全注意事项

### 4.1 Burner 账户限制

| 限制 | 后果 | 应对 |
|------|------|------|
| 公网入站规则 (0.0.0.0/0 inbound) | **账户自动关闭** | Terraform 已配置 private subnet + SSM，不要手动创建 SG |
| S3 API 限制 | `GetBucketVersioning` 等 API 被 SCP 阻止 | Terraform 已移除相关资源定义 |
| 7 天自动删除 | 所有资源丢失 | 实验数据及时 `sync-to-s3.sh`，然后下载到本地 |

### 4.2 凭证管理

- **永远不要**在代码中硬编码 AWS 凭证
- EC2 通过 IAM Instance Profile 获取临时凭证（自动轮换）
- 本地 Terraform 通过 AWS CLI profile 认证
- LiteLLM 通过 EC2 Instance Profile 调用 Bedrock（无需 API key）
- CUA Bridge 通过 boto3 默认凭证链调用 Bedrock

---

## 5. 成本估算

| 资源 | 每小时 | 每天（24h） | 每周（7天） | 说明 |
|------|--------|------------|------------|------|
| r6i.4xlarge (Platform) | ~$1.01 | ~$24.19 | ~$169.34 | 16 vCPU, 128GB RAM |
| r6i.2xlarge (WebArena) | ~$0.50 | ~$12.10 | ~$84.67 | 8 vCPU, 64GB RAM |
| NAT Gateway | ~$0.045 | ~$1.08 | ~$7.56 | + 数据传输费 |
| VPC Endpoints (4 Interface) | ~$0.04 | ~$0.96 | ~$6.72 | SSM×3 + Bedrock |
| EBS (100GB gp3 + 1000GB gp3) | ~$0.012 | ~$0.29 | ~$2.00 | Platform + WebArena 磁盘 |
| S3 | 忽略不计 | — | — | |
| Bedrock LLM 调用 | 变动 | ~$10-50/pilot | ~$30-150 | 取决于实验规模 |
| **合计（不含 LLM）** | **~$1.57** | **~$37.62** | **~$263.35** |
| **合计（含 LLM 估算）** | — | — | **~$300-420** | |

**省钱建议**：不跑实验时 stop EC2 instances（`aws ec2 stop-instances`），EBS 仍计费但 EC2 计算费停止。NAT Gateway 和 VPC Endpoints 7×24 计费，如果长时间不用可以 terraform destroy 再重建。

---

## 6. 常见问题排查

### 6.1 Terraform apply 失败

| 错误 | 原因 | 解决 |
|------|------|------|
| `EntityAlreadyExists` (IAM Role) | 之前的 state 丢失，IAM role 残留 | `terraform import aws_iam_role.<name> <role-name>` |
| `InvalidAMIID.NotFound` | AMI 不在当前 region | 确认 region 是 us-east-2 |
| `UnauthorizedAccess` | 凭证过期或错误账户 | `aws sts get-caller-identity` 确认 |
| `VcpuLimitExceeded` | 新账户 vCPU 配额不足 | 在 Service Quotas 中申请提升 |

### 6.2 SSM 连接失败

| 错误 | 原因 | 解决 |
|------|------|------|
| `TargetNotConnected` | SSM Agent 未启动或 VPC Endpoint 未就绪 | 等待 5 分钟后重试；检查 VPC Endpoint 状态 |
| `SessionManagerPlugin not found` | 本地未安装 SSM Plugin | 安装 Session Manager Plugin |

### 6.3 Bedrock 403

| 错误 | 原因 | 解决 |
|------|------|------|
| `AccessDeniedException` | 模型未开通 | Bedrock 控制台 → Model Access → 申请 |
| `403 from VPC Endpoint` | Region 不匹配 | 确认 litellm_config.yaml 和 cua_bridge.py 中的 region 与 VPC Endpoint 一致 |
| IAM policy 不足 | 缺少 `inference-profile/*` | 检查 IAM policy 是否包含 geo-inference ARN |

### 6.4 Magento 302 Redirect

这是最常见的部署问题。症状：Playwright 访问 shopping URL 返回 `ERR_CONNECTION_REFUSED`。

原因：Magento 的 `base_url` 配置指向错误的 hostname（Docker 内部 URL 或公网 hostname）。

解决：见 §3.3 中的手动修复步骤。

---

## 7. 修改项速查表

按优先级排序，部署新账户时依次检查：

```
✅ 必须修改
├── infra/terraform.tfvars          — 新建，填入账户信息
├── infra/main.tf                   — profile 名称（如果不用 a11y-pilot）
├── config-pilot4.yaml              — WebArena IP（sed 批量替换）
├── config-pilot4-cua.yaml          — WebArena IP
├── config-regression.yaml          — WebArena IP
├── config-reinject-smoke.yaml      — WebArena IP
├── config-pilot.yaml               — WebArena IP
├── config-pilot2.yaml              — WebArena IP
├── config-pilot3.yaml              — WebArena IP
├── config-pilot3b.yaml             — WebArena IP
├── config-vision-smoke.yaml        — WebArena IP
├── config-cua-smoke.yaml           — WebArena IP
├── .kiro/steering/project-context.md — EC2 instance IDs
└── EC2 环境变量 WA_*               — WebArena IP

⚠️ 换 Region 时才需要修改（保持 us-east-2 则不需要）
├── infra/webarena.tf               — AMI ID
├── litellm_config.yaml             — 所有 aws_region_name
├── src/runner/cua_bridge.py        — BEDROCK_REGION
├── scripts/smoke-cua-bedrock-direct.py — REGION
├── scripts/sync-to-s3.sh           — REGION 默认值
└── infra/main.tf                   — Bedrock IAM policy ARN regions

🔧 可选修改
├── infra/main.tf                   — instance_type（按预算调整）
├── infra/webarena.tf               — instance_type, volume_size
└── infra/main.tf                   — github_repo URL
```
