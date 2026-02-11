// Module: IAM (creates roles/policies for lambdas and step functions)
module "iam" {
  source = "./modules/iam"
}

// Module: S3 (creates artifact bucket)
module "s3" {
  source = "./modules/s3"
  name_prefix = "${var.project}-${var.env}"
}

// Module: Lambda (creates ingestion and compliance Lambda functions)
module "lambda" {
  source = "./modules/lambda"

  s3_bucket                 = module.s3.bucket_id
  ingestion_filename          = var.ingestion_zip_path
  compliance_filename        = var.compliance_zip_path
  # ingestion_s3_key           = var.ingestion_zip_s3_key
  # compliance_s3_key          = var.compliance_zip_s3_key

  ingestion_function_name   = "${var.project}-${var.env}-ingestion-lambda"
  compliance_function_name  = "${var.project}-${var.env}-compliance-lambda"

  ingestion_role_arn        = module.iam.ingestion_lambda_role_arn
  compliance_role_arn       = module.iam.compliance_lambda_role_arn
}

// Module: Step Functions (orchestrates invocation of lambdas)
module "step_functions" {
  source = "./modules/step-functions"

  name   = "${var.project}-${var.env}-state-machine"

  # Execution role for Step Functions
  step_functions_role_arn   = module.iam.step_functions_role_arn

  # Render ASL template and inject lambda ARNs for ingestion and compliance
  definition = templatefile("${path.module}/step_functions/contract_review.asl.json", {
    ingestion_lambda_arn  = module.lambda.ingestion_lambda_arn
    compliance_lambda_arn = module.lambda.compliance_lambda_arn
  })

}

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
