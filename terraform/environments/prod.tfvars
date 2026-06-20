environment         = "prod"
github_org          = "YOUR_GITHUB_ORG"
github_repo         = "YOUR_GITHUB_REPO"
tf_state_bucket     = "YOUR_TFSTATE_BUCKET"
tf_state_lock_table = "YOUR_TFSTATE_LOCK_TABLE"

app_image    = "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/flask-boilerplate/app:latest"
worker_image = "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/flask-boilerplate/worker:latest"

# RDS: Multi-AZ, backups enabled, deletion protection on
rds_instance_class      = "db.t3.small"
rds_deletion_protection = true
rds_backup_retention    = 7
rds_multi_az            = true
rds_skip_final_snapshot = false

redis_node_type = "cache.t3.micro"

# Two tasks for availability
ecs_cpu           = 1024
ecs_memory        = 2048
ecs_desired_count = 2

# Required for prod — provision via ACM before applying
certificate_arn = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/YOUR_CERT_ID"

waf_rate_limit = 1000
