output "instance_id" {
  description = "EC2 instance ID — use with: aws ssm start-session --target <id>"
  value       = aws_instance.platform.id
}

output "s3_bucket_name" {
  description = "S3 bucket for experiment data"
  value       = aws_s3_bucket.data.id
}

output "ssm_connect_command" {
  description = "Command to connect via SSM Session Manager"
  value       = "aws ssm start-session --target ${aws_instance.platform.id} --region ${var.aws_region}"
}

output "ssm_port_forward_command" {
  description = "Port forward LiteLLM (4000) to localhost for testing"
  value       = "aws ssm start-session --target ${aws_instance.platform.id} --document-name AWS-StartPortForwardingSession --parameters portNumber=4000,localPortNumber=4000 --region ${var.aws_region}"
}
