locals {
  prefix = "${var.app_name}-${var.environment}"
}

resource "aws_ecs_cluster" "main" {
  name = local.prefix

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.prefix}/app"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.prefix}-app"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = "app"
    image     = var.app_image
    essential = true

    portMappings = [{
      containerPort = var.container_port
      protocol      = "tcp"
    }]

    # Sensitive values injected from Secrets Manager at container startup
    secrets = [
      { name = "DATABASE_URL", valueFrom = var.database_url_secret_arn },
      { name = "JWT_SECRET_KEY", valueFrom = var.jwt_secret_arn },
      { name = "SECRET_KEY", valueFrom = var.flask_secret_arn },
    ]

    # Non-sensitive config as plain environment variables
    environment = [
      { name = "FLASK_APP", value = "wsgi.py" },
      { name = "FLASK_ENV", value = "production" },
      { name = "REST_API_V", value = "v1" },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      { name = "AWS_S3_BUCKET", value = var.s3_bucket },
      { name = "SQS_QUEUE_URL", value = var.sqs_queue_url },
      { name = "REDIS_URL", value = var.redis_url },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "app"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}/api/v1/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_ecs_service" "app" {
  name            = "${local.prefix}-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "app"
    container_port   = var.container_port
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    # CI/CD pipeline manages task_definition and desired_count after initial deploy
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_ecs_task_definition.app]
}
