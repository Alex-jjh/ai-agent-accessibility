output "instance_public_ip" {
  description = "Public IP of the platform EC2 instance"
  value       = aws_instance.platform.public_ip
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.platform.id
}

output "s3_bucket_name" {
  description = "S3 bucket for experiment data"
  value       = aws_s3_bucket.data.id
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh -i ${var.ssh_public_key_path} ec2-user@${aws_instance.platform.public_ip}"
}
