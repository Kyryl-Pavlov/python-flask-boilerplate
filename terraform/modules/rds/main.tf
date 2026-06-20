locals {
  prefix  = "${var.app_name}-${var.environment}"
  db_name = replace(var.app_name, "-", "_")
}

resource "random_password" "db" {
  length  = 32
  special = false # RDS password cannot contain / @ " space
  keepers = { version = "1" }
}

resource "aws_db_subnet_group" "main" {
  name       = local.prefix
  subnet_ids = var.subnet_ids
}

resource "aws_db_instance" "main" {
  identifier        = local.prefix
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.instance_class
  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = local.db_name
  username = "appuser"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false

  multi_az                  = var.multi_az
  deletion_protection       = var.deletion_protection
  backup_retention_period   = var.backup_retention
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.prefix}-final"

  performance_insights_enabled = true

  lifecycle {
    ignore_changes = [password]
  }
}

# Store the full DATABASE_URL in Secrets Manager so ECS/Lambda can inject it directly.
resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${local.prefix}/database-url"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql://${aws_db_instance.main.username}:${random_password.db.result}@${aws_db_instance.main.endpoint}/${local.db_name}"
}
