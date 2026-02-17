// Module: IAM (creates roles/policies for lambdas and step functions)
module "iam" {
  source = "./modules/iam"
}

// Module: S3 (creates artifact bucket)
module "s3" {
  source = "./modules/s3"
  name_prefix = "${var.project}-${var.env}"
}

// Module: Lambda (creates ingestion, compliance, invoke_sfn Lambda functions)
module "lambda" {
  source = "./modules/lambda"

  s3_bucket                 = module.s3.bucket_id
  ingestion_filename        = var.ingestion_zip_path
  compliance_filename       = var.compliance_zip_path
  invoke_filename          = var.invoke_zip_path
  risk_analysis_filename   = var.risk_analysis_zip_path

  ingestion_function_name   = "${var.project}-${var.env}-ingestion-lambda"
  compliance_function_name  = "${var.project}-${var.env}-compliance-lambda"
  invoke_function_name      = "${var.project}-${var.env}-invoke-sfn-lambda"
  risk_analysis_function_name = "${var.project}-${var.env}-risk-analysis-lambda"

  ingestion_role_arn        = module.iam.ingestion_lambda_role_arn
  compliance_role_arn       = module.iam.compliance_lambda_role_arn
  invoke_role_arn           = module.iam.invoke_sfn_lambda_role_arn
  risk_analysis_role_arn    = module.iam.risk_analysis_lambda_role_arn
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

// Allow S3 to invoke the invoke_sfn lambda
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.invoke_sfn_lambda_arn
  principal     = "s3.amazonaws.com"
  source_arn    = module.s3.bucket_arn
}

resource "aws_s3_bucket_notification" "artifacts_notification" {
  bucket = module.s3.bucket_id

  lambda_function {
    lambda_function_arn = module.lambda.invoke_sfn_lambda_arn
    events              = ["s3:ObjectCreated:Put"]
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}
