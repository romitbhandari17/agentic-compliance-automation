// infra/variables.tf

variable "region" {
  description = "AWS region to deploy into"
  type        = string
}

variable "env" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
}

variable "project" {
  description = "Project name"
  type        = string
}

variable "ingestion_zip_path" {
  description = "Name of the ingestion lambda"
  type        = string
  default     = ""
}

variable "compliance_zip_path" {
  description = "Name of the compliance lambda"
  type        = string
  default     = ""
}

variable "ingestion_zip_s3_key" {
  description = "S3 key where ingestion lambda zip is stored (optional)"
  type        = string
  default     = ""
}

variable "compliance_zip_s3_key" {
  description = "S3 key where compliance lambda zip is stored (optional)"
  type        = string
  default     = ""
}

variable "invoke_zip_path" {
  description = "Path to invoke_sfn lambda zip package"
  type        = string
  default     = ""
}
