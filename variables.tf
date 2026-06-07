variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-southeast-2"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d{1}$", var.aws_region))
    error_message = "The aws_region must be a valid AWS region format (e.g., us-east-1, eu-west-2)."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "s3-vectors-rag-demo"

  validation {
    condition     = length(var.project_name) >= 1 && length(var.project_name) <= 64
    error_message = "The project_name must be between 1 and 64 characters."
  }
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "The environment must be one of: dev, staging, prod."
  }
}

variable "source_bucket_prefix" {
  description = "Prefix for the source documents S3 bucket name"
  type        = string
  default     = "rag-source-docs"

  validation {
    condition     = length(var.source_bucket_prefix) >= 3 && length(var.source_bucket_prefix) <= 37
    error_message = "The source_bucket_prefix must be between 3 and 37 characters."
  }
}

variable "vector_bucket_name" {
  description = "Name for the S3 Vectors bucket"
  type        = string
  default     = "rag-vectors"

  validation {
    condition     = length(var.vector_bucket_name) >= 3 && length(var.vector_bucket_name) <= 63
    error_message = "The vector_bucket_name must be between 3 and 63 characters."
  }
}

variable "vector_index_name" {
  description = "Name for the vector index within the S3 Vectors bucket"
  type        = string
  default     = "rag-embeddings"

  validation {
    condition     = length(var.vector_index_name) >= 3 && length(var.vector_index_name) <= 63
    error_message = "The vector_index_name must be between 3 and 63 characters."
  }
}

variable "vector_dimension" {
  description = "Dimensionality of the vector embeddings (must match the embedding model output)"
  type        = number
  default     = 1024

  validation {
    condition     = var.vector_dimension >= 1 && var.vector_dimension <= 4096
    error_message = "The vector_dimension must be between 1 and 4096."
  }
}

variable "vector_distance_metric" {
  description = "Distance metric for vector similarity search"
  type        = string
  default     = "cosine"

  validation {
    condition     = contains(["cosine", "euclidean"], var.vector_distance_metric)
    error_message = "The vector_distance_metric must be one of: cosine, euclidean."
  }
}

variable "embedding_model_id" {
  description = "Bedrock model identifier for generating text embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"

  validation {
    condition     = length(var.embedding_model_id) > 0
    error_message = "The embedding_model_id must not be empty."
  }
}

variable "llm_model_id" {
  description = "Bedrock model identifier for LLM text generation"
  type        = string
  default     = "au.anthropic.claude-sonnet-4-5-20250929-v1:0"

  validation {
    condition     = length(var.llm_model_id) > 0
    error_message = "The llm_model_id must not be empty."
  }
}

variable "ingest_schedule_expression" {
  description = "EventBridge schedule for daily AWS news corpus ingest (UTC)"
  type        = string
  default     = "cron(0 6 * * ? *)"
}

variable "cognito_admin_email" {
  description = "Email for the initial admin Cognito user (empty skips user creation)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "cognito_admin_password" {
  description = "Permanent password for the initial admin Cognito user (auto-generated when empty)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "cognito_callback_urls" {
  description = "Additional Cognito callback URLs for the SPA client"
  type        = list(string)
  default     = []
}

variable "cognito_logout_urls" {
  description = "Additional Cognito logout URLs for the SPA client"
  type        = list(string)
  default     = []
}

variable "api_throttle_rate" {
  description = "API Gateway steady-state throttle (requests per second)"
  type        = number
  default     = 10
}

variable "api_throttle_burst" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 50
}
