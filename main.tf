locals {
  bucket_prefix      = random_id.bucket_prefix.hex
  source_bucket_name = "${local.bucket_prefix}-${var.source_bucket_prefix}-${var.project_name}-${var.environment}"
  vector_bucket_name = "${local.bucket_prefix}-${var.vector_bucket_name}"
  amplify_origin     = "https://main.${aws_amplify_app.ui.default_domain}"
}

resource "random_id" "bucket_prefix" {
  byte_length = 4
}

resource "random_password" "cognito_admin" {
  count = var.cognito_admin_email != "" && var.cognito_admin_password == "" ? 1 : 0

  length           = 16
  special          = true
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
  override_special = "!@#$%&*-_=+"
}
