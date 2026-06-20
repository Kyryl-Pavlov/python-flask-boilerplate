output "redis_url" {
  description = "Redis connection URL for use in REDIS_URL env var."
  value       = "rediss://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379/0"
}
