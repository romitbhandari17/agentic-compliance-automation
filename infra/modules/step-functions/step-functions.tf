resource "aws_sfn_state_machine" "this" {
  name       = var.name
  role_arn   = var.step_functions_role_arn
  definition = var.definition
  # type       = lookup(var, "state_machine_type", "STANDARD")

  tags = var.tags
}