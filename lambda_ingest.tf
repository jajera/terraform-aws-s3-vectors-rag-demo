data "archive_file" "ingest_lambda" {
  type        = "zip"
  output_path = "${path.module}/.build/ingest-lambda.zip"

  source {
    content  = file("${path.module}/lambda/ingest/handler.py")
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

resource "aws_iam_role" "ingest_lambda" {
  name = "${var.project_name}-${var.environment}-ingest-lambda"

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

resource "aws_iam_role_policy" "ingest_lambda" {
  name = "${var.project_name}-${var.environment}-ingest-lambda"
  role = aws_iam_role.ingest_lambda.id

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
        Resource = "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-${var.environment}-ingest:*"
      },
      {
        Sid    = "S3SourceBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.source_documents.arn,
          "${aws_s3_bucket.source_documents.arn}/*"
        ]
      },
      {
        Sid    = "S3VectorsAccess"
        Effect = "Allow"
        Action = [
          "s3vectors:PutVectors",
          "s3vectors:QueryVectors",
          "s3vectors:GetVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:ListIndexes"
        ]
        Resource = "${aws_s3vectors_vector_bucket.this.vector_bucket_arn}/*"
      },
      {
        Sid    = "BedrockInvokeModel"
        Effect = "Allow"
        Action = "bedrock:InvokeModel"
        Resource = [
          "arn:aws:bedrock:${data.aws_region.current.region}::foundation-model/${var.embedding_model_id}",
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "ingest" {
  function_name = "${var.project_name}-${var.environment}-ingest"
  role          = aws_iam_role.ingest_lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 480
  memory_size   = 512

  filename         = data.archive_file.ingest_lambda.output_path
  source_code_hash = data.archive_file.ingest_lambda.output_base64sha256

  environment {
    variables = {
      SOURCE_BUCKET      = aws_s3_bucket.source_documents.id
      VECTOR_BUCKET      = aws_s3vectors_vector_bucket.this.vector_bucket_name
      VECTOR_INDEX       = aws_s3vectors_index.this.index_name
      EMBEDDING_MODEL_ID = var.embedding_model_id
      LLM_MODEL_ID       = var.llm_model_id
    }
  }

  depends_on = [aws_iam_role_policy.ingest_lambda]
}

resource "aws_cloudwatch_log_group" "ingest_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.ingest.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_event_rule" "ingest_schedule" {
  name                = "${var.project_name}-${var.environment}-ingest-daily"
  description         = "Daily AWS news corpus ingest for RAG demo"
  schedule_expression = var.ingest_schedule_expression
}

resource "aws_cloudwatch_event_target" "ingest_schedule" {
  rule      = aws_cloudwatch_event_rule.ingest_schedule.name
  target_id = "ingest-lambda"
  arn       = aws_lambda_function.ingest.arn

  input = jsonencode({
    source = "eventbridge"
  })
}

resource "aws_lambda_permission" "ingest_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingest_schedule.arn
}

resource "aws_lambda_permission" "ingest_query" {
  statement_id  = "AllowQueryLambdaInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "lambda.amazonaws.com"
  source_arn    = aws_lambda_function.query.arn
}

resource "aws_lambda_invocation" "ingest_bootstrap" {
  function_name = aws_lambda_function.ingest.function_name

  input = jsonencode({
    source = "terraform"
  })

  depends_on = [
    aws_lambda_function.ingest,
    aws_s3vectors_index.this,
    aws_iam_role_policy.ingest_lambda,
  ]

  lifecycle {
    replace_triggered_by = [
      aws_lambda_function.ingest.source_code_hash,
    ]
  }
}
