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

# Note: bucket notifications and lambda permissions are declared at the root infra level
# to avoid module circular dependencies.
