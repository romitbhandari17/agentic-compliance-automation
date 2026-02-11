// infra/modules/s3/outputs.tf

output "bucket_id" {
  description = "S3 bucket id (name)"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "S3 bucket arn"
  value       = aws_s3_bucket.this.arn
}

