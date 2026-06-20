locals {
  prefix = "${var.app_name}-${var.environment}"
}

resource "aws_elasticache_subnet_group" "main" {
  name       = local.prefix
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = local.prefix
  description          = "Redis for ${local.prefix}"
  node_type            = var.node_type
  num_cache_clusters   = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.1"
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [var.security_group_id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  automatic_failover_enabled = false

  snapshot_retention_limit = 1
}
