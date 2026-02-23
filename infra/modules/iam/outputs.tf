// Outputs: role ARNs and role names for ingestion, compliance, and step functions roles
output "ingestion_lambda_role_arn" {
  description = "ARN of the ingestion Lambda execution role"
  value       = aws_iam_role.ingestion_lambda_role.arn
}

output "ingestion_lambda_role_name" {
  description = "Name of the ingestion Lambda execution role"
  value       = aws_iam_role.ingestion_lambda_role.name
}

output "compliance_lambda_role_arn" {
  description = "ARN of the compliance Lambda execution role"
  value       = aws_iam_role.compliance_lambda_role.arn
}

output "compliance_lambda_role_name" {
  description = "Name of the compliance Lambda execution role"
  value       = aws_iam_role.compliance_lambda_role.name
}

output "step_functions_role_arn" {
  description = "ARN of the Step Functions execution role"
  value       = aws_iam_role.step_functions_role.arn
}

output "step_functions_role_name" {
  description = "Name of the Step Functions execution role"
  value       = aws_iam_role.step_functions_role.name
}

output "invoke_sfn_lambda_role_arn" {
  description = "ARN of the invoke-sfn Lambda execution role"
  value       = aws_iam_role.invoke_sfn_lambda_role.arn
}

output "invoke_sfn_lambda_role_name" {
  description = "Name of the invoke-sfn Lambda execution role"
  value       = aws_iam_role.invoke_sfn_lambda_role.name
}

output "risk_analysis_lambda_role_arn" {
  description = "ARN of the risk analysis Lambda execution role"
  value       = aws_iam_role.risk_analysis_lambda_role.arn
}

output "risk_analysis_lambda_role_name" {
  description = "Name of the risk analysis Lambda execution role"
  value       = aws_iam_role.risk_analysis_lambda_role.name
}

output "decision_lambda_role_arn" {
  description = "ARN of the decision Lambda execution role"
  value       = aws_iam_role.decision_lambda_role.arn
}

output "decision_lambda_role_name" {
  description = "Name of the decision Lambda execution role"
  value       = aws_iam_role.decision_lambda_role.name
}
