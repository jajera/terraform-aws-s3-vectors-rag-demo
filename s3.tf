resource "aws_s3_bucket" "source_documents" {
  bucket        = local.source_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "source_documents" {
  bucket = aws_s3_bucket.source_documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "source_documents" {
  bucket = aws_s3_bucket.source_documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "source_documents" {
  bucket = aws_s3_bucket.source_documents.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.source_documents.arn,
          "${aws_s3_bucket.source_documents.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}
