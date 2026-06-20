variable "app_name" {
  description = "Application name used as a prefix for all resources."
  type        = string
  default     = "flask-boilerplate"
}

variable "environment" {
  description = "Deployment environment."
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be 'dev' or 'prod'."
  }
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

# ── Networking ───────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to use (at least 2 required for RDS Multi-AZ)."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets — one per AZ."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets — one per AZ."
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

# ── RDS ──────────────────────────────────────────────────────────────────────

variable "rds_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_deletion_protection" {
  description = "Enable deletion protection on the RDS instance."
  type        = bool
  default     = false
}

variable "rds_backup_retention" {
  description = "Days to retain automated RDS backups (0 disables backups)."
  type        = number
  default     = 1
}

variable "rds_multi_az" {
  description = "Enable Multi-AZ standby for RDS."
  type        = bool
  default     = false
}

variable "rds_skip_final_snapshot" {
  description = "Skip final snapshot when the RDS instance is destroyed."
  type        = bool
  default     = true
}

# ── ElastiCache ──────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t3.micro"
}

# ── ECS ──────────────────────────────────────────────────────────────────────

variable "ecs_cpu" {
  description = "vCPU units for the ECS task (256 / 512 / 1024 / 2048 / 4096)."
  type        = number
  default     = 512
}

variable "ecs_memory" {
  description = "Memory for the ECS task in MiB."
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Desired number of running ECS task instances."
  type        = number
  default     = 1
}

variable "app_image" {
  description = <<-EOT
    Full ECR image URI for the Flask app.
    Must exist in ECR before the first full terraform apply.
    Bootstrap: run `terraform apply -target=module.ecr`, push your image, then apply the rest.
    Example: 123456789.dkr.ecr.us-east-1.amazonaws.com/flask-boilerplate/app:latest
  EOT
  type        = string
}

variable "worker_image" {
  description = <<-EOT
    Full ECR image URI for the Lambda/worker container.
    Same bootstrap requirement as app_image.
    Example: 123456789.dkr.ecr.us-east-1.amazonaws.com/flask-boilerplate/worker:latest
  EOT
  type        = string
}

# ── ALB ──────────────────────────────────────────────────────────────────────

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS on the ALB. Leave empty for HTTP-only (dev)."
  type        = string
  default     = ""
}

# ── WAF ──────────────────────────────────────────────────────────────────────

variable "waf_rate_limit" {
  description = "Max requests per IP per 5-minute window before WAF blocks."
  type        = number
  default     = 1000
}

# ── GitHub OIDC ──────────────────────────────────────────────────────────────

variable "github_org" {
  description = "GitHub organisation or username that owns the repository."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (without org prefix)."
  type        = string
}

variable "tf_state_bucket" {
  description = "Name of the S3 bucket that holds Terraform state (the one you created during bootstrap)."
  type        = string
}

variable "tf_state_lock_table" {
  description = "Name of the DynamoDB table used for Terraform state locking."
  type        = string
}
