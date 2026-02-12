// Root outputs to expose convenient attributes
output "ingestion_lambda_arn" {
  description = "ARN of the ingestion Lambda created by the lambda module"
  value       = module.lambda.ingestion_lambda_arn
}

output "ingestion_lambda_name" {
  description = "Name of the ingestion Lambda created by the lambda module"
  value       = module.lambda.ingestion_lambda_name
}

output "compliance_lambda_arn" {
  description = "ARN of the compliance Lambda created by the lambda module"
  value       = module.lambda.compliance_lambda_arn
}

output "compliance_lambda_name" {
  description = "Name of the compliance Lambda created by the lambda module"
  value       = module.lambda.compliance_lambda_name
}

output "invoke_lambda_arn" {
  description = "ARN of the invoke_sfn Lambda created by the lambda module"
  value       = module.lambda.invoke_sfn_lambda_arn
}

output "invoke_lambda_name" {
  description = "Name of the invoke_sfn Lambda created by the lambda module"
  value       = module.lambda.invoke_sfn_lambda_name
}

output "ingestion_role_arn" {
  description = "ARN of the ingestion Lambda execution role"
  value       = module.iam.ingestion_lambda_role_arn
}

output "compliance_role_arn" {
  description = "ARN of the compliance Lambda execution role"
  value       = module.iam.compliance_lambda_role_arn
}

output "step_functions_role_arn" {
  description = "ARN of the Step Functions execution role"
  value       = module.iam.step_functions_role_arn
}
