 modules/bastion/main.tf
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# Create a key pair for SSH access
resource "aws_key_pair" "bastion" {
  key_name   = "${var.name_prefix}-bastion-key"
  public_key = var.ssh_public_key
}

# IAM Role for SSM
resource "aws_iam_role" "bastion_ssm_role" {
  name = "${var.name_prefix}-bastion-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion-ssm-role"
  })
}

resource "aws_iam_role_policy_attachment" "bastion_ssm_policy" {
  role       = aws_iam_role.bastion_ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}


resource "aws_iam_instance_profile" "bastion_profile" {
  name = "${var.name_prefix}-bastion-instance-profile"
  role = aws_iam_role.bastion_ssm_role.name

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion-instance-profile"
  })
}

resource "aws_security_group" "bastion" {
  name_prefix = "${var.name_prefix}-bastion-"
  vpc_id      = var.vpc_id
  description = "Security group for bastion host"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "SSH access from allowed IPs"
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.vpc_cidr_blocks
    description = "HTTPS to VPC for SSM endpoints"
  }
  
  egress {
    from_port   = 5432 
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.vpc_cidr_blocks
    description = "Database access within VPC"
  }
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion-sg"
  })
}

resource "aws_instance" "bastion" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.bastion.key_name
  subnet_id                   = var.public_subnet_id
  vpc_security_group_ids      = [aws_security_group.bastion.id]
  iam_instance_profile        = aws_iam_instance_profile.bastion_profile.name
  associate_public_ip_address = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens = "required"
  }
  
  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y postgresql
    
    # Ensure SSM agent is running (should be by default on Amazon Linux 2)
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
  EOF
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-bastion-host"
  })
}
