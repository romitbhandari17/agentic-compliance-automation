// infra/modules/s3/s3.tf
// Creates an S3 bucket to hold deployment artifacts (lambda zips) with versioning enabled

resource "aws_s3_bucket" "this" {
  bucket = "${var.name_prefix}-s3-artifacts"
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = "Enabled"
  }
}
