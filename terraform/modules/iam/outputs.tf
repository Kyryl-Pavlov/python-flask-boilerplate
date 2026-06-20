output "ecs_task_execution_role_arn" {
  value = aws_iam_role.ecs_task_execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.ecs_task.arn
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda.arn
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}
