output "source_bucket_name" {
  description = "Name of the S3 bucket for uploading source documents to the RAG pipeline"
  value       = aws_s3_bucket.source_documents.id
}

output "vector_bucket_name" {
  description = "Name of the S3 Vectors bucket for storing document embeddings"
  value       = aws_s3vectors_vector_bucket.this.vector_bucket_name
}

output "vector_index_name" {
  description = "Name of the vector index for put and query operations"
  value       = aws_s3vectors_index.this.index_name
}

output "vector_index_arn" {
  description = "ARN of the vector index resource"
  value       = aws_s3vectors_index.this.index_arn
}

output "embedding_model_id" {
  description = "Bedrock model identifier used for generating text embeddings"
  value       = var.embedding_model_id
}

output "llm_model_id" {
  description = "Bedrock model identifier used for LLM text generation"
  value       = var.llm_model_id
}

output "aws_region" {
  description = "AWS region where all resources are deployed"
  value       = var.aws_region
}

output "ingest_function_name" {
  description = "Lambda function that ingests AWS news RSS into S3 and S3 Vectors"
  value       = aws_lambda_function.ingest.function_name
}

output "ingest_schedule_expression" {
  description = "EventBridge cron expression for scheduled corpus ingest (UTC)"
  value       = var.ingest_schedule_expression
}

output "app_url" {
  description = "HTTPS URL for the Amplify-hosted briefing UI"
  value       = "https://main.${aws_amplify_app.ui.default_domain}"
}

output "api_endpoint" {
  description = "HTTPS API Gateway endpoint for authenticated RAG operations"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Cognito app client ID for the SPA"
  value       = aws_cognito_user_pool_client.spa.id
}

output "cognito_domain" {
  description = "Cognito hosted UI domain prefix"
  value       = aws_cognito_user_pool_domain.main.domain
}

output "cognito_hosted_ui_url" {
  description = "Cognito hosted UI base URL"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cognito_admin_email" {
  description = "Email of the Terraform-managed admin user (empty if not created)"
  value       = var.cognito_admin_email != "" ? var.cognito_admin_email : null
  sensitive   = true
}

output "cognito_admin_password" {
  description = "Admin password (auto-generated unless cognito_admin_password was set in tfvars)"
  value       = var.cognito_admin_email != "" ? local.cognito_admin_password : null
  sensitive   = true
}
