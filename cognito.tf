resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-${var.environment}"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_pool_client" "spa" {
  name         = "${var.project_name}-${var.environment}-spa"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  supported_identity_providers = ["COGNITO"]

  prevent_user_existence_errors = "ENABLED"

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  callback_urls = concat(
    ["https://main.${aws_amplify_app.ui.default_domain}"],
    var.cognito_callback_urls,
  )

  logout_urls = concat(
    ["https://main.${aws_amplify_app.ui.default_domain}"],
    var.cognito_logout_urls,
  )

  allowed_oauth_flows_user_pool_client = false
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${var.environment}-rag"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "aws_cognito_user_group" "admins" {
  name         = "admins"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Users who may trigger corpus re-ingest"
}

locals {
  cognito_admin_password = var.cognito_admin_password != "" ? var.cognito_admin_password : (
    var.cognito_admin_email != "" ? random_password.cognito_admin[0].result : ""
  )
}

resource "aws_cognito_user" "admin" {
  count        = var.cognito_admin_email != "" ? 1 : 0
  user_pool_id = aws_cognito_user_pool.main.id
  username     = var.cognito_admin_email

  attributes = {
    email          = var.cognito_admin_email
    email_verified = "true"
  }

  password                 = local.cognito_admin_password
  message_action           = "SUPPRESS"
  desired_delivery_mediums = []

  lifecycle {
    ignore_changes = [password]
  }
}

resource "aws_cognito_user_in_group" "admin" {
  count        = var.cognito_admin_email != "" ? 1 : 0
  user_pool_id = aws_cognito_user_pool.main.id
  username     = aws_cognito_user.admin[0].username
  group_name   = aws_cognito_user_group.admins.name
}
