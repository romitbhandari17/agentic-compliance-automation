// infra/modules/lambda/outputs.tf

output "ingestion_lambda_arn" {
  description = "ARN of the ingestion Lambda function"
  value       = aws_lambda_function.ingestion.arn
}

output "ingestion_lambda_name" {
  description = "Name of the ingestion Lambda function"
  value       = aws_lambda_function.ingestion.function_name
}

output "compliance_lambda_arn" {
  description = "ARN of the compliance Lambda function"
  value       = aws_lambda_function.compliance.arn
}

output "compliance_lambda_name" {
  description = "Name of the compliance Lambda function"
  value       = aws_lambda_function.compliance.function_name
}

