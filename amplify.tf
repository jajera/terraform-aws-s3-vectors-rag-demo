resource "aws_amplify_app" "ui" {
  name     = "${var.project_name}-${var.environment}-ui"
  platform = "WEB"

  custom_rule {
    source = "/<*>"
    status = "404-200"
    target = "/index.html"
  }
}

resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.ui.id
  branch_name = "main"
  framework   = "Web"
  stage       = "PRODUCTION"
}

resource "null_resource" "deploy_web" {
  triggers = {
    web_hash = sha256(join("", [
      for f in sort(fileset("${path.module}/web", "**")) :
      filesha256("${path.module}/web/${f}")
    ]))
    api_endpoint         = aws_apigatewayv2_stage.default.invoke_url
    cognito_client_id    = aws_cognito_user_pool_client.spa.id
    cognito_user_pool_id = aws_cognito_user_pool.main.id
    cognito_domain       = aws_cognito_user_pool_domain.main.domain
  }

  provisioner "local-exec" {
    command     = "${path.module}/scripts/deploy-web.sh"
    working_dir = path.module
    environment = {
      AWS_REGION           = var.aws_region
      API_ENDPOINT         = aws_apigatewayv2_stage.default.invoke_url
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
      COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.spa.id
      COGNITO_DOMAIN       = aws_cognito_user_pool_domain.main.domain
      AMPLIFY_APP_ID       = aws_amplify_app.ui.id
      AMPLIFY_BRANCH       = aws_amplify_branch.main.branch_name
    }
  }

  depends_on = [
    aws_amplify_branch.main,
    aws_apigatewayv2_stage.default,
    aws_cognito_user_pool_client.spa,
    aws_lambda_function.query,
  ]
}
