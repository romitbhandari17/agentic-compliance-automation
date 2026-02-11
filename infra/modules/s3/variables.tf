// infra/modules/s3/variables.tf

variable "name_prefix" {
  description = "Optional explicit bucket name to use instead of the default"
  type        = string
  default     = ""
}

// Optional outputs can be added by the s3 module implementation later
