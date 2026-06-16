variable "aws_region" {
  description = "AWS region to create the state bucket and lock table in."
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for Terraform state. Convention: <your-org>-<app>-tfstate"
  type        = string
}

variable "lock_table_name" {
  description = "DynamoDB table name for Terraform state locking."
  type        = string
  default     = "flask-boilerplate-tfstate-lock"
}
