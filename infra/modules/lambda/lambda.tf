// infra/modules/lambda/lambda.tf
// Lambda module: defines two Lambda functions (ingestion and compliance)

resource "aws_lambda_function" "ingestion" {
  function_name = var.ingestion_function_name

  # Support either local file deployment or S3-based deployment. If filename is
  # provided, it will be used; otherwise s3_bucket/s3_key are used.
  filename         = var.ingestion_filename
  source_code_hash = filebase64sha256(var.ingestion_filename)

  # Only set s3_bucket/s3_key when s3_key is provided (non-empty). Terraform
  # requires both to be present if one is used.
  # s3_bucket = length(var.ingestion_s3_key) > 0 ? var.s3_bucket : null
  # s3_key    = length(var.ingestion_s3_key) > 0 ? var.ingestion_s3_key : null

  handler       = "main.handler"
  runtime       = "python3.10"
  role          = var.ingestion_role_arn
  timeout       = var.ingestion_timeout
}

resource "aws_lambda_function" "compliance" {
  function_name = var.compliance_function_name
  filename         = var.compliance_filename
  source_code_hash = filebase64sha256(var.compliance_filename)

  # s3_bucket = length(var.compliance_s3_key) > 0 ? var.s3_bucket : null
  # s3_key    = length(var.compliance_s3_key) > 0 ? var.compliance_s3_key : null

  handler       = "agents.compliance.main.handler"
  runtime       = "python3.10"
  role          = var.compliance_role_arn
  timeout       = var.compliance_timeout
}

resource "aws_lambda_function" "invoke_sfn" {
  function_name = var.invoke_function_name
  filename         = var.invoke_filename
  source_code_hash = length(var.invoke_filename) > 0 ? filebase64sha256(var.invoke_filename) : null
  handler       = "main.handler"
  runtime       = "python3.10"
  role          = var.invoke_role_arn
  timeout       = var.invoke_timeout
}

resource "aws_lambda_function" "risk_analysis" {
  function_name = var.risk_analysis_function_name

  filename         = length(var.risk_analysis_filename) > 0 ? var.risk_analysis_filename : null
  source_code_hash = length(var.risk_analysis_filename) > 0 ? filebase64sha256(var.risk_analysis_filename) : null

  handler       = "main.handler"
  runtime       = "python3.10"
  role          = var.risk_analysis_role_arn
  timeout       = var.risk_analysis_timeout
}

resource "aws_lambda_function" "decision" {
  function_name = var.decision_function_name

  filename         = length(var.decision_filename) > 0 ? var.decision_filename : null
  source_code_hash = length(var.decision_filename) > 0 ? filebase64sha256(var.decision_filename) : null

  handler       = "agents.decision.main.handler"
  runtime       = "python3.10"
  role          = var.decision_role_arn
  timeout       = var.decision_timeout
}
