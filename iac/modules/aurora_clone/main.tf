# Aurora Database Clone Module for Data Science Workloads

locals {
  name_prefix = "${var.app_name}-${var.environment}-datasci"

  tags = merge(
    var.tags,
    {
      Name        = "${local.name_prefix}-aurora-clone"
      Environment = var.environment
      Purpose     = "data-science"
      Module      = "aurora_clone"
      Terraform   = "true"
    }
  )
}

# Create a snapshot of the source Aurora cluster
resource "aws_db_cluster_snapshot" "source" {
  count = var.create_snapshot ? 1 : 0

  db_cluster_identifier          = var.source_cluster_id
  db_cluster_snapshot_identifier = "${var.source_cluster_id}-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  tags = merge(local.tags, {
    SourceCluster = var.source_cluster_id
    CreatedAt     = timestamp()
  })

  lifecycle {
    ignore_changes = [db_cluster_snapshot_identifier]
  }
}

# Security Group for the cloned Aurora cluster
resource "aws_security_group" "aurora_clone" {
  name        = "${local.name_prefix}-aurora-clone-sg"
  description = "Security group for cloned Aurora PostgreSQL for data science"
  # vpc_id      = var.vpc_id

  egress {
    from_port
