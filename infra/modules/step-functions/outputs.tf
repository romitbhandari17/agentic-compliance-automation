output "state_machine_name" {
  value       = aws_sfn_state_machine.this.name
  description = "Name of the Step Functions state machine"
}

output "state_machine_arn" {
  value       = aws_sfn_state_machine.this.arn
  description = "ARN of the Step Functions state machine"
}

