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

output "invoke_sfn_lambda_arn" {
  description = "ARN of the invoke_sfn Lambda function"
  value       = aws_lambda_function.invoke_sfn.arn
}

output "invoke_sfn_lambda_name" {
  description = "Name of the invoke_sfn Lambda function"
  value       = aws_lambda_function.invoke_sfn.function_name
}

output "risk_analysis_lambda_arn" {
  description = "ARN of the compliance Lambda function"
  value       = aws_lambda_function.risk_analysis.arn
}

output "risk_analysis_lambda_name" {
  description = "Name of the compliance Lambda function"
  value       = aws_lambda_function.risk_analysis.function_name
}

output "decision_lambda_arn" {
  description = "ARN of the decision Lambda function"
  value       = aws_lambda_function.decision.arn
}

output "decision_lambda_name" {
  description = "Name of the decision Lambda function"
  value       = aws_lambda_function.decision.function_name
}
