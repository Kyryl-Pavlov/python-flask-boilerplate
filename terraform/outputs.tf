# Run `terraform output` after apply to get the values for GitHub environment vars.

output "alb_dns_name" {
  description = "DNS name of the ALB. Point your domain's CNAME here."
  value       = module.alb.alb_dns_name
}

# ── GitHub Actions environment vars (Settings → Environments → dev / production) ─

output "ecs_cluster" {
  description = "→ GitHub var: ECS_CLUSTER"
  value       = module.ecs.cluster_name
}

output "ecs_service" {
  description = "→ GitHub var: ECS_SERVICE"
  value       = module.ecs.service_name
}

output "app_task_family" {
  description = "→ GitHub var: APP_TASK_FAMILY"
  value       = module.ecs.task_definition_family
}

output "vpc_subnets" {
  description = "→ GitHub var: VPC_SUBNETS (comma-separated)"
  value       = join(",", module.networking.private_subnet_ids)
}

output "vpc_security_groups" {
  description = "→ GitHub var: VPC_SECURITY_GROUPS"
  value       = module.networking.ecs_security_group_id
}

output "lambda_function_name" {
  description = "→ GitHub var: LAMBDA_FUNCTION_NAME"
  value       = module.lambda.function_name
}

# ── GitHub Actions secrets (Settings → Secrets → Actions) ─────────────────

output "github_actions_role_arn" {
  description = "→ GitHub secret: AWS_ROLE_ARN"
  value       = module.iam.github_actions_role_arn
}

# ── ECR ──────────────────────────────────────────────────────────────────────

output "ecr_app_repository_url" {
  description = "ECR URL for the Flask app — use in app_image tfvar after first push."
  value       = module.ecr.app_repository_url
}

output "ecr_worker_repository_url" {
  description = "ECR URL for the worker — use in worker_image tfvar after first push."
  value       = module.ecr.worker_repository_url
}
