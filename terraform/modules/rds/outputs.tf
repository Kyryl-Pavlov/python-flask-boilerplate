output "database_url_secret_arn" {
  description = "Secrets Manager ARN for the full DATABASE_URL string."
  value       = aws_secretsmanager_secret.database_url.arn
}

output "endpoint" {
  value = aws_db_instance.main.endpoint
}
