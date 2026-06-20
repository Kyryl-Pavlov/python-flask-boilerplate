locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

data "aws_caller_identity" "current" {}

# ── Networking ───────────────────────────────────────────────────────────────

module "networking" {
  source = "./modules/networking"

  app_name             = var.app_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

# ── ECR ──────────────────────────────────────────────────────────────────────

module "ecr" {
  source = "./modules/ecr"

  app_name    = var.app_name
  environment = var.environment
}

# ── Data stores ──────────────────────────────────────────────────────────────

module "rds" {
  source = "./modules/rds"

  app_name            = var.app_name
  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  subnet_ids          = module.networking.private_subnet_ids
  security_group_id   = module.networking.rds_security_group_id
  instance_class      = var.rds_instance_class
  deletion_protection = var.rds_deletion_protection
  backup_retention    = var.rds_backup_retention
  multi_az            = var.rds_multi_az
  skip_final_snapshot = var.rds_skip_final_snapshot
}

module "elasticache" {
  source = "./modules/elasticache"

  app_name          = var.app_name
  environment       = var.environment
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.redis_security_group_id
  node_type         = var.redis_node_type
}

module "s3" {
  source = "./modules/s3"

  app_name    = var.app_name
  environment = var.environment
}

module "sqs" {
  source = "./modules/sqs"

  app_name    = var.app_name
  environment = var.environment
}

# ── Application secrets ───────────────────────────────────────────────────────
# Randomly generated on first apply; rotated by changing the keeper value.

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
  keepers = { version = "1" }
}

resource "random_password" "flask_secret" {
  length  = 64
  special = true
  keepers = { version = "1" }
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name                    = "${local.name_prefix}/jwt-secret-key"
  recovery_window_in_days = 7
  # 7 days = AWS minimum; gives a recovery window without blocking name reuse for long.
  # Note: terraform destroy + immediate apply will fail while the secret is pending deletion.
  # Either wait 7 days, restore the secret, or temporarily set to 0 for full rebuild cycles.
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = random_password.jwt_secret.result
}

resource "aws_secretsmanager_secret" "flask_secret" {
  name                    = "${local.name_prefix}/secret-key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "flask_secret" {
  secret_id     = aws_secretsmanager_secret.flask_secret.id
  secret_string = random_password.flask_secret.result
}

# ── IAM ──────────────────────────────────────────────────────────────────────

module "iam" {
  source = "./modules/iam"

  app_name            = var.app_name
  environment         = var.environment
  aws_account_id      = data.aws_caller_identity.current.account_id
  aws_region          = var.aws_region
  s3_bucket_arn       = module.s3.bucket_arn
  sqs_queue_arn       = module.sqs.queue_arn
  ecr_app_repo_arn    = module.ecr.app_repository_arn
  ecr_worker_repo_arn = module.ecr.worker_repository_arn
  secret_arns = [
    module.rds.database_url_secret_arn,
    aws_secretsmanager_secret.jwt_secret.arn,
    aws_secretsmanager_secret.flask_secret.arn,
  ]
  github_org          = var.github_org
  github_repo         = var.github_repo
  tf_state_bucket     = var.tf_state_bucket
  tf_state_lock_table = var.tf_state_lock_table
}

# ── Traffic ───────────────────────────────────────────────────────────────────

module "alb" {
  source = "./modules/alb"

  app_name          = var.app_name
  environment       = var.environment
  vpc_id            = module.networking.vpc_id
  public_subnet_ids = module.networking.public_subnet_ids
  security_group_id = module.networking.alb_security_group_id
  certificate_arn   = var.certificate_arn
  health_check_path = "/api/v1/health"
}

module "waf" {
  source = "./modules/waf"

  app_name    = var.app_name
  environment = var.environment
  alb_arn     = module.alb.alb_arn
  rate_limit  = var.waf_rate_limit
}

# ── Compute ───────────────────────────────────────────────────────────────────

module "ecs" {
  source = "./modules/ecs"

  app_name                = var.app_name
  environment             = var.environment
  aws_region              = var.aws_region
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  security_group_id       = module.networking.ecs_security_group_id
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn
  app_image               = var.app_image
  cpu                     = var.ecs_cpu
  memory                  = var.ecs_memory
  desired_count           = var.ecs_desired_count
  target_group_arn        = module.alb.target_group_arn
  container_port          = 5000
  database_url_secret_arn = module.rds.database_url_secret_arn
  jwt_secret_arn          = aws_secretsmanager_secret.jwt_secret.arn
  flask_secret_arn        = aws_secretsmanager_secret.flask_secret.arn
  redis_url               = module.elasticache.redis_url
  s3_bucket               = module.s3.bucket_name
  sqs_queue_url           = module.sqs.queue_url
}

module "lambda" {
  source = "./modules/lambda"

  app_name                = var.app_name
  environment             = var.environment
  aws_region              = var.aws_region
  worker_image            = var.worker_image
  role_arn                = module.iam.lambda_role_arn
  security_group_id       = module.networking.lambda_security_group_id
  subnet_ids              = module.networking.private_subnet_ids
  sqs_queue_arn           = module.sqs.queue_arn
  database_url_secret_arn = module.rds.database_url_secret_arn
  redis_url               = module.elasticache.redis_url
  s3_bucket               = module.s3.bucket_name
}
