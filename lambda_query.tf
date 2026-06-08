data "archive_file" "query_lambda" {
  type        = "zip"
  output_path = "${path.module}/.build/query-lambda.zip"

  source {
    content  = file("${path.module}/lambda/query/handler.py")
    filename = "handler.py"
  }

  dynamic "source" {
    for_each = fileset("${path.module}/rag", "*.py")
    content {
      content  = file("${path.module}/rag/${source.value}")
      filename = "rag/${source.value}"
    }
  }
}

resource "aws_iam_role" "query_lambda" {
  name = "${var.project_name}-${var.environment}-query-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "query_lambda" {
  name = "${var.project_name}-${var.environment}-query-lambda"
  role = aws_iam_role.query_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-query:*"
      },
      {
        Sid    = "S3SourceBucketRead"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.source_documents.arn,
          "${aws_s3_bucket.source_documents.arn}/*"
        ]
      },
      {
        Sid    = "S3VectorsQuery"
        Effect = "Allow"
        Action = [
          "s3vectors:QueryVectors",
          "s3vectors:GetVectors",
          "s3vectors:ListIndexes"
        ]
        Resource = "${aws_s3vectors_vector_bucket.this.vector_bucket_arn}/*"
      },
      {
        Sid    = "BedrockInvokeModel"
        Effect = "Allow"
        Action = "bedrock:InvokeModel"
        Resource = concat(
          [
            "arn:aws:bedrock:${data.aws_region.current.region}::foundation-model/${var.embedding_model_id}",
            "arn:aws:bedrock:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:inference-profile/${var.llm_model_id}",
          ],
          [
            for region in ["ap-southeast-2", "ap-southeast-4"] :
            "arn:aws:bedrock:${region}::foundation-model/${local.llm_foundation_model_id}"
          ]
        )
      },
      {
        Sid      = "InvokeIngestLambda"
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.ingest.arn
      }
    ]
  })
}

resource "aws_lambda_function" "query" {
  function_name = "${var.project_name}-${var.environment}-query"
  role          = aws_iam_role.query_lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 512

  filename         = data.archive_file.query_lambda.output_path
  source_code_hash = data.archive_file.query_lambda.output_base64sha256

  environment {
    variables = {
      SOURCE_BUCKET        = aws_s3_bucket.source_documents.id
      VECTOR_BUCKET        = aws_s3vectors_vector_bucket.this.vector_bucket_name
      VECTOR_INDEX         = aws_s3vectors_index.this.index_name
      EMBEDDING_MODEL_ID   = var.embedding_model_id
      LLM_MODEL_ID         = var.llm_model_id
      INGEST_FUNCTION_NAME = aws_lambda_function.ingest.function_name
      CORS_ALLOW_ORIGIN    = local.amplify_origin
    }
  }

  depends_on = [aws_iam_role_policy.query_lambda]
}

resource "aws_cloudwatch_log_group" "query_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.query.function_name}"
  retention_in_days = 14
}

resource "aws_lambda_permission" "query_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rag.execution_arn}/*/*"
}
