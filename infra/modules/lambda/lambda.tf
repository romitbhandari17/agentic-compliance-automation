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

  handler       = "main.handler"
  runtime       = "python3.10"
  role          = var.compliance_role_arn
  timeout       = var.compliance_timeout
}
