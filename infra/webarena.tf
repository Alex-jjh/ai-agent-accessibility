###############################################################################
# WebArena Instance — Same VPC, Private Subnet, SSM Access
#
# Uses official WebArena AMI (us-east-2 only).
# Communicates with platform EC2 via private IP within the same VPC.
# No public IP, no SSH — access via SSM.
###############################################################################

# ---------- IAM for WebArena (SSM access) ----------

resource "aws_iam_role" "webarena" {
  name = "${var.project_name}-webarena-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  tags = { Name = "${var.project_name}-webarena-role" }
}

resource "aws_iam_role_policy_attachment" "webarena_ssm" {
  role       = aws_iam_role.webarena.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "webarena" {
  name = "${var.project_name}-webarena-profile"
  role = aws_iam_role.webarena.name
}

# ---------- WebArena EC2 (same private subnet) ----------

resource "aws_instance" "webarena" {
  ami                    = "ami-08a862bf98e3bd7aa" # WebArena pre-installed AMI (us-east-2)
  instance_type          = "t3a.2xlarge"
  vpc_security_group_ids = [aws_security_group.instance.id]  # Same SG as platform
  subnet_id              = aws_subnet.private.id              # Same private subnet
  iam_instance_profile   = aws_iam_instance_profile.webarena.name

  # NO key pair, NO public IP — SSM only

  root_block_device {
    volume_size = 1000  # WebArena needs ~1TB
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = base64encode(<<-USERDATA
    #!/bin/bash
    set -euo pipefail

    # Install SSM agent (WebArena AMI is Ubuntu, may not have it)
    snap install amazon-ssm-agent --classic || true
    systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service || true
    systemctl start snap.amazon-ssm-agent.amazon-ssm-agent.service || true

    # Start all WebArena Docker containers
    docker start gitlab shopping shopping_admin forum kiwix33 || true

    # Wait for services
    sleep 60

    # Get private IP for base URL config
    PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

    docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://$PRIVATE_IP:7770/" || true
    docker exec shopping mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://$PRIVATE_IP:7770/' WHERE path = 'web/secure/base_url';" || true
    docker exec shopping /var/www/magento2/bin/magento cache:flush || true

    docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://$PRIVATE_IP:7780/" || true
    docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://$PRIVATE_IP:7780/' WHERE path = 'web/secure/base_url';" || true
    docker exec shopping_admin /var/www/magento2/bin/magento cache:flush || true

    docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_is_forced 0 || true
    docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_lifetime 0 || true

    docker exec gitlab update-permissions || true
    docker exec gitlab sed -i "s|^external_url.*|external_url 'http://$PRIVATE_IP:8023'|" /etc/gitlab/gitlab.rb || true
    docker exec gitlab gitlab-ctl reconfigure || true

    echo "=== WebArena setup complete ==="
  USERDATA
  )

  tags = { Name = "${var.project_name}-webarena" }

  depends_on = [
    aws_vpc_endpoint.ssm,
    aws_vpc_endpoint.ssmmessages,
    aws_vpc_endpoint.ec2messages,
  ]
}

# WebArena ports are defined as inline ingress in main.tf security group
