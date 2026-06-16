output "bucket_name" {
  description = "Copy this into backend.hcl → bucket and dev/prod.tfvars → tf_state_bucket"
  value       = aws_s3_bucket.tfstate.bucket
}

output "lock_table_name" {
  description = "Copy this into backend.hcl → dynamodb_table and dev/prod.tfvars → tf_state_lock_table"
  value       = aws_dynamodb_table.tfstate_lock.name
}

output "next_steps" {
  value = <<-EOT

    Bootstrap complete. Now:

    1. Copy values above into terraform/backend.hcl
    2. Copy values above into terraform/environments/dev.tfvars and prod.tfvars
    3. cd ../  (back to terraform/)
    4. terraform init -backend-config=backend.hcl
    5. terraform apply -target=module.ecr -var-file=environments/dev.tfvars
    6. Push images to ECR, set app_image / worker_image in dev.tfvars
    7. terraform apply -var-file=environments/dev.tfvars

  EOT
}
