locals {
  prefix = "${var.app_name}-${var.environment}"
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${local.prefix}-worker"
  retention_in_days = 30
}

resource "aws_lambda_function" "worker" {
  function_name = "${local.prefix}-worker"
  role          = var.role_arn
  package_type  = "Image"
  image_uri     = var.worker_image
  timeout       = 300
  memory_size   = 512

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      AWS_S3_BUCKET           = var.s3_bucket
      REDIS_URL               = var.redis_url
      SQS_QUEUE_URL           = var.sqs_queue_url
      # DATABASE_URL is fetched from Secrets Manager at runtime via boto3
      DATABASE_URL_SECRET_ARN = var.database_url_secret_arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.worker]

  lifecycle {
    # CI/CD pipeline manages image_uri after initial deploy
    ignore_changes = [image_uri]
  }
}

# Trigger Lambda from SQS
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn                   = var.sqs_queue_arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  enabled                            = true
}
