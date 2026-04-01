###############################################################################
# WebArena Instance — us-east-2 (Ohio)
#
# Uses the official WebArena pre-installed AMI.
# This is a separate instance from the platform instance (us-east-1).
# The platform connects to WebArena apps via the public IP.
###############################################################################

provider "aws" {
  alias  = "ohio"
  region = "us-east-2"
}

# ---------- Networking (minimal — public subnet in default VPC) ----------

data "aws_vpc" "default_ohio" {
  provider = aws.ohio
  default  = true
}

data "aws_subnets" "default_ohio" {
  provider = aws.ohio
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default_ohio.id]
  }
}

# ---------- Security Group ----------

resource "aws_security_group" "webarena" {
  provider    = aws.ohio
  name_prefix = "${var.project_name}-webarena-sg-"
  vpc_id      = data.aws_vpc.default_ohio.id
  description = "WebArena apps: SSH + app ports + all outbound"

  # SSH
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # WebArena app ports
  dynamic "ingress" {
    for_each = [3000, 7770, 7780, 8023, 8888, 9999]
    content {
      description = "WebArena port ${ingress.value}"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-webarena-sg" }
}

# ---------- SSH Key (reuse same public key in ohio) ----------

resource "aws_key_pair" "webarena" {
  provider   = aws.ohio
  key_name   = "${var.project_name}-webarena-key"
  public_key = file(var.ssh_public_key_path)
}

# ---------- EC2 Instance ----------

resource "aws_instance" "webarena" {
  provider               = aws.ohio
  ami                    = "ami-08a862bf98e3bd7aa" # WebArena pre-installed AMI (us-east-2)
  instance_type          = "t3a.xlarge"            # 4 vCPU, 16GB RAM (WebArena recommended)
  key_name               = aws_key_pair.webarena.key_name
  vpc_security_group_ids = [aws_security_group.webarena.id]
  subnet_id              = data.aws_subnets.default_ohio.ids[0]

  associate_public_ip_address = true

  root_block_device {
    volume_size = 1000  # WebArena recommends 1000GB
    volume_type = "gp3"
    encrypted   = true
  }

  user_data = base64encode(<<-USERDATA
    #!/bin/bash
    set -euo pipefail

    # Start all WebArena Docker containers
    docker start gitlab shopping shopping_admin forum kiwix33 || true

    # Wait for services to initialize
    sleep 60

    # Configure shopping URLs with public hostname
    HOSTNAME=$(curl -s http://169.254.169.254/latest/meta-data/public-hostname)

    docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://$HOSTNAME:7770" || true
    docker exec shopping mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://$HOSTNAME:7770/' WHERE path = 'web/secure/base_url';" || true
    docker exec shopping /var/www/magento2/bin/magento cache:flush || true

    docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://$HOSTNAME:7780" || true
    docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e "UPDATE core_config_data SET value='http://$HOSTNAME:7780/' WHERE path = 'web/secure/base_url';" || true
    docker exec shopping_admin /var/www/magento2/bin/magento cache:flush || true

    docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_is_forced 0 || true
    docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_lifetime 0 || true

    docker exec gitlab update-permissions || true
    docker exec gitlab sed -i "s|^external_url.*|external_url 'http://$HOSTNAME:8023'|" /etc/gitlab/gitlab.rb || true
    docker exec gitlab gitlab-ctl reconfigure || true

    echo "=== WebArena setup complete ==="
  USERDATA
  )

  tags = {
    Name = "${var.project_name}-webarena"
  }
}

# ---------- Outputs ----------

output "webarena_public_ip" {
  description = "Public IP of the WebArena instance"
  value       = aws_instance.webarena.public_ip
}

output "webarena_public_hostname" {
  description = "Public hostname of the WebArena instance"
  value       = aws_instance.webarena.public_dns
}

output "webarena_ssh_command" {
  description = "SSH command for WebArena instance"
  value       = "ssh -i ${var.ssh_public_key_path} ubuntu@${aws_instance.webarena.public_ip}"
}

output "webarena_urls" {
  description = "WebArena app URLs"
  value = {
    reddit     = "http://${aws_instance.webarena.public_ip}:9999"
    gitlab     = "http://${aws_instance.webarena.public_ip}:8023"
    shopping   = "http://${aws_instance.webarena.public_ip}:7770"
    cms        = "http://${aws_instance.webarena.public_ip}:7780"
    wikipedia  = "http://${aws_instance.webarena.public_ip}:8888"
    map        = "http://${aws_instance.webarena.public_ip}:3000"
  }
}
