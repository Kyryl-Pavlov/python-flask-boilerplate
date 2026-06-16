variable "app_name" { type = string }
variable "environment" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_id" { type = string }
variable "node_type" { type = string }
