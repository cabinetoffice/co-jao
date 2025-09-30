# modules/bastion/outputs.tf

output "bastion_public_ip" {
  description = "Public IP address of the bastion host"
  value       = aws_instance.bastion.public_ip
}

output "bastion_private_ip" {
  description = "Private IP address of the bastion host"
  value       = aws_instance.bastion.private_ip
}

output "bastion_instance_id" {
  description = "Instance ID of the bastion host"
  value       = aws_instance.bastion.id
}

output "bastion_security_group_id" {
  description = "Security group ID of the bastion host"
  value       = aws_security_group.bastion.id
}

output "ssh_key_name" {
  description = "Name of the SSH key pair for bastion access"
  value       = aws_key_pair.bastion.key_name
}

output "connection_instructions" {
  description = "Instructions for connecting through the bastion"
  value = <<EOF
To connect to your Aurora database through the bastion:

1. SSH to bastion:
   ssh -i ~/.ssh/id_rsa ec2-user@${aws_instance.bastion.public_ip}

2. Create SSH tunnel:
   ssh -i ~/.ssh/id_rsa -L 5433:${var.aurora_endpoint}:5432 ec2-user@${aws_instance.bastion.public_ip}

3. Connect to database using local port:
   psql -h localhost -p 5433 -U dbadmin -d jaodevdb
EOF
}
