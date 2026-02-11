variable "name" {
  description = "Name of the Step Functions state machine"
  type        = string
}

variable "step_functions_role_arn" {
  description = "ARN for the Step Functions execution role"
  type        = string
}

variable "definition" {
  description = "ASL definition for the state machine"
  type        = string
}

variable "tags" {
  description = "Tags to apply to the state machine"
  type        = map(string)
  default     = {}
}

