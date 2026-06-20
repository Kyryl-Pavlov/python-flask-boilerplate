output "app_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "app_repository_arn" {
  value = aws_ecr_repository.app.arn
}

output "worker_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "worker_repository_arn" {
  value = aws_ecr_repository.worker.arn
}
