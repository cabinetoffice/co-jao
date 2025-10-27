# modules/bastion/variables.tf

variable "name_prefix" {
  description = "Prefix for naming resources"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where bastion will be created"
  type        = string
}

variable "vpc_cidr_blocks" {
  description = "CIdR blocks for bastion to connect to services"
  type = list(string)
}

variable "public_subnet_id" {
  description = "Public subnet ID for bastion host"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to SSH to bastion"
  type        = list(string)
  
  validation {
    condition = !contains(var.allowed_cidr_blocks, "0.0.0.0/0") && !contains(var.allowed_cidr_blocks, "::/0")
    error_message = "allowed_cidr_blocks cannot contain 0.0.0.0/0 or ::/0"
  }
}

variable "ssh_public_key" {
  description = "SSH public key for bastion access"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for bastion host"
  type        = string
  default     = "t3.nano"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "aurora_endpoint" {
  description = "Aurora cluster endpoint for connection instructions"
  type        = string
}

