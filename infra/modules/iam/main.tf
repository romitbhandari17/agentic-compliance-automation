// infra/modules/iam/main.tf
// IAM module: roles and policies for ingestion lambda, compliance lambda, and step functions

// Assume role policy for Lambda service principal
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

// Ingestion Lambda execution role
resource "aws_iam_role" "ingestion_lambda_role" {
  name               = "ingestion-lambda-execution-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

// Compliance Lambda execution role
resource "aws_iam_role" "compliance_lambda_role" {
  name               = "compliance-lambda-execution-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

// More specific inline policy for Ingestion Lambda role
// - S3: Get/Put/List
// - CloudWatch Logs: Create/Put/Get
// - Bedrock: model invocation-related actions (kept as service-specific action names)
// - Textract: document analysis/detection actions
// Resources remain as ["*"] placeholders to be replaced with concrete ARNs later
data "aws_iam_policy_document" "ingestion_lambda_policy" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
      "logs:GetLogEvents"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      // Bedrock actions - kept explicit where known; adjust later if needed
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:DescribeModel"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      // Textract common actions used for synchronous and asynchronous processing
      "textract:AnalyzeDocument",
      "textract:DetectDocumentText",
      "textract:GetDocumentAnalysis",
      "textract:GetDocumentTextDetection",
      "textract:StartDocumentAnalysis",
      "textract:StartDocumentTextDetection"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "ingestion_lambda_inline" {
  name   = "ingestion-lambda-inline-policy"
  role   = aws_iam_role.ingestion_lambda_role.id
  policy = data.aws_iam_policy_document.ingestion_lambda_policy.json
}

// More specific inline policy for Compliance Lambda role
// - S3: Get/Put/List
// - CloudWatch Logs: Create/Put/Get
// - Bedrock: model invocation-related actions
// Resources remain as ["*"] placeholders to be replaced with concrete ARNs later
data "aws_iam_policy_document" "compliance_lambda_policy" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
      "logs:GetLogEvents"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:DescribeModel"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "compliance_lambda_inline" {
  name   = "compliance-lambda-inline-policy"
  role   = aws_iam_role.compliance_lambda_role.id
  policy = data.aws_iam_policy_document.compliance_lambda_policy.json
}

// Assume role policy for Step Functions service principal
data "aws_iam_policy_document" "step_functions_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "step_functions_role" {
  name               = "step-functions-execution-role"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume_role.json
}

// Policy for Step Functions role to invoke Lambdas and write logs
// Resources are kept as ["*"] placeholders; replace with specific ARNs when available
data "aws_iam_policy_document" "step_functions_policy" {
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction",
      "lambda:InvokeAsync"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "step_functions_inline" {
  name   = "step-functions-inline-policy"
  role   = aws_iam_role.step_functions_role.id
  policy = data.aws_iam_policy_document.step_functions_policy.json
}

// Notes:
// - Actions and resources use wildcards now as placeholders; replace with least-privilege ARNs/actions later.
// - This file only contains IAM/Lambda-related role and inline policy changes as requested.
