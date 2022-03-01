output "arn" {
  description = "ARN of the lambda"
  value       = aws_lambda_function.lambda_update_levels_table.arn
}

output "id" {
  description = "id of the lambda"
  value       = aws_lambda_function.lambda_update_levels_table.id
}


output "iam_role_id" {
  value = aws_iam_role.iam_for_lambda.id
}

output "iam_name" {
  value = aws_iam_role.iam_for_lambda.name
}