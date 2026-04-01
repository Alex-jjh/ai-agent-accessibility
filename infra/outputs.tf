output "instance_id" {
  description = "Platform EC2 instance ID"
  value       = aws_instance.platform.id
}

output "webarena_instance_id" {
  description = "WebArena EC2 instance ID"
  value       = aws_instance.webarena.id
}

output "webarena_private_ip" {
  description = "WebArena private IP (use this in config.yaml)"
  value       = aws_instance.webarena.private_ip
}

output "s3_bucket_name" {
  value = aws_s3_bucket.data.id
}

output "ssm_platform" {
  description = "Connect to platform EC2"
  value       = "aws ssm start-session --target ${aws_instance.platform.id} --region ${var.aws_region}"
}

output "ssm_webarena" {
  description = "Connect to WebArena EC2"
  value       = "aws ssm start-session --target ${aws_instance.webarena.id} --region ${var.aws_region}"
}

output "webarena_urls" {
  description = "WebArena app URLs (use private IP from platform EC2)"
  value = {
    shopping       = "http://${aws_instance.webarena.private_ip}:7770"
    shopping_admin = "http://${aws_instance.webarena.private_ip}:7780"
    reddit         = "http://${aws_instance.webarena.private_ip}:9999"
    gitlab         = "http://${aws_instance.webarena.private_ip}:8023"
    wikipedia      = "http://${aws_instance.webarena.private_ip}:8888"
  }
}
