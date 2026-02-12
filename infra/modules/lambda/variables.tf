// infra/modules/lambda/variables.tf

variable "s3_bucket" {
  description = "S3 bucket where Lambda deployment packages are stored"
  type        = string
}

variable "ingestion_filename" {
  description = "path for ingestion lambda deployment package"
  type        = string
}

variable "compliance_filename" {
  description = "path for compliance lambda deployment package"
  type        = string
}

variable "ingestion_function_name" {
  description = "Name for the ingestion Lambda function"
  type        = string
  default     = "ingestion-lambda"
}

variable "compliance_function_name" {
  description = "Name for the compliance Lambda function"
  type        = string
  default     = "compliance-lambda"
}

variable "ingestion_role_arn" {
  description = "IAM role ARN to attach to the ingestion Lambda"
  type        = string
}

variable "compliance_role_arn" {
  description = "IAM role ARN to attach to the compliance Lambda"
  type        = string
}

// Optional S3 key arguments if you want to deploy from S3 instead of local filename
variable "ingestion_s3_key" {
  description = "S3 key for the ingestion lambda zip (optional)"
  type        = string
  default     = ""
}

variable "compliance_s3_key" {
  description = "S3 key for the compliance lambda zip (optional)"
  type        = string
  default     = ""
}

// New timeout variables (seconds)
variable "ingestion_timeout" {
  description = "Timeout for the ingestion Lambda function in seconds"
  type        = number
  default     = 300
}

variable "compliance_timeout" {
  description = "Timeout for the compliance Lambda function in seconds"
  type        = number
  default     = 300
}
