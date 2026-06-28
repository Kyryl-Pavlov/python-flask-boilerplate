output "app_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "app_repository_name" {
  value = aws_ecr_repository.app.name
}

output "app_repository_arn" {
  value = aws_ecr_repository.app.arn
}

output "worker_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "worker_repository_name" {
  value = aws_ecr_repository.worker.name
}

output "worker_repository_arn" {
  value = aws_ecr_repository.worker.arn
}
