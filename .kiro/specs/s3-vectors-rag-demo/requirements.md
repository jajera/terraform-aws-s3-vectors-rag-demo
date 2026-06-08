# Requirements Document

## Introduction

This document defines the requirements for a cloud-native AWS announcements briefing demo that provisions S3 Vectors, Amazon Bedrock, Lambda, API Gateway, Cognito, and Amplify resources via Terraform. The system automatically ingests AWS What's New and AWS News Blog RSS feeds, generates embeddings, stores vectors, and serves a web UI where authenticated users can ask questions grounded in recent AWS announcements. The project follows Terraform demo conventions: flat structure, snake_case identifiers, consistent tagging, GitHub Actions CI, and single-region AWS deployment.

## Glossary

- **Terraform_Configuration**: The set of `.tf` files that define AWS infrastructure resources
- **S3_Vectors_Bucket**: An AWS S3 bucket with the Vectors feature enabled for storing and querying vector embeddings
- **Source_Documents_Bucket**: A standard AWS S3 bucket used to store ingested RSS article documents
- **Bedrock_Runtime**: The Amazon Bedrock service used for embedding generation and LLM inference
- **Embedding_Model**: Amazon Titan Embeddings V2 used to convert text into 1024-dimensional vector representations
- **LLM**: Anthropic Claude (via AU cross-region inference profile) used for generating natural language answers
- **RAG_Pipeline**: The end-to-end workflow of embedding a query, searching S3 Vectors, and generating an answer via the LLM
- **Ingest_Lambda**: AWS Lambda function that fetches RSS feeds, uploads articles to S3, and stores vector embeddings
- **Query_Lambda**: AWS Lambda function that handles API requests for querying the RAG pipeline and triggering ingests
- **API_Gateway**: AWS API Gateway HTTP API with JWT authorization for routing requests to Query_Lambda
- **Cognito_User_Pool**: AWS Cognito user pool providing authentication and group-based authorization
- **Amplify_App**: AWS Amplify hosting for the static SPA web frontend
- **CI_Workflows**: GitHub Actions workflow files that perform linting, validation, and commit message conformance checks
- **Tagging_Standard**: The convention of applying Project, Environment, and ManagedBy tags to all taggable AWS resources
- **Vector_Index**: A named index within S3_Vectors_Bucket that defines the dimensionality and distance metric for stored embeddings

## Requirements

### Requirement 1: Repository Structure

**User Story:** As a developer, I want the repository to follow a flat Terraform structure with consistent conventions, so that the project is easy to navigate and maintain.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL use a flat directory structure with no nested modules or environment directories
2. THE Terraform_Configuration SHALL use snake_case for all Terraform resource names, variable names, and output names
3. THE Terraform_Configuration SHALL include a `versions.tf` file specifying `required_version >= 1.5.0` and provider versions
4. THE Terraform_Configuration SHALL include a `providers.tf` file containing the AWS provider configuration with default_tags
5. THE Terraform_Configuration SHALL include a `variables.tf` file with validation blocks on applicable variables
6. THE Terraform_Configuration SHALL include an `outputs.tf` file with descriptive output values
7. THE Terraform_Configuration SHALL include a `terraform.tfvars` file with user-configurable values annotated with `# REPLACE` comments
8. THE Terraform_Configuration SHALL include a `.gitignore` file covering tfstate files, .terraform directory, tfvars.local, crash logs, Python artifacts, and build outputs

### Requirement 2: Resource Tagging

**User Story:** As an operations engineer, I want all AWS resources tagged consistently, so that I can track ownership, environment, and management tooling.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL apply a `Project` tag to every taggable AWS resource via default_tags
2. THE Terraform_Configuration SHALL apply an `Environment` tag to every taggable AWS resource via default_tags
3. THE Terraform_Configuration SHALL apply a `ManagedBy` tag with value `Terraform` to every taggable AWS resource via default_tags
4. THE Terraform_Configuration SHALL define Project and Environment as configurable variables in `variables.tf`

### Requirement 3: Security and Access Control

**User Story:** As a security-conscious developer, I want authentication, authorization, and least-privilege IAM, so that the demo follows security best practices.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL rely exclusively on environment variables or AWS credential files for Terraform authentication
2. THE Terraform_Configuration SHALL define separate IAM roles per Lambda function with minimum required permissions
3. WHEN the Ingest_Lambda requires access, THE policy SHALL scope to only the specific S3, S3 Vectors, and Bedrock resources needed
4. WHEN the Query_Lambda requires access, THE policy SHALL scope to only the specific S3, S3 Vectors, Bedrock, and Lambda invoke resources needed
5. THE Terraform_Configuration SHALL enable S3 bucket policies that deny unencrypted transport (enforce TLS)
6. THE API_Gateway SHALL use Cognito JWT authorization on all authenticated routes
7. THE `POST /ingest` route SHALL require the user to be in the Cognito `admins` group
8. THE API_Gateway SHALL enforce configurable rate and burst throttling limits

### Requirement 4: Source Documents Bucket

**User Story:** As a user, I want an S3 bucket provisioned for storing ingested RSS articles, so that the ingest pipeline has a location to store corpus documents.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL provision a Source_Documents_Bucket with a globally unique name using a random prefix
2. THE Source_Documents_Bucket SHALL have versioning enabled
3. THE Source_Documents_Bucket SHALL have server-side encryption enabled using SSE-S3
4. THE Source_Documents_Bucket SHALL have force_destroy enabled for easy demo teardown
5. THE Source_Documents_Bucket SHALL enforce TLS-only access via a bucket policy

### Requirement 5: S3 Vectors Bucket

**User Story:** As a user, I want an S3 Vectors bucket provisioned for storing article embeddings, so that the system can perform similarity searches.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL provision an S3_Vectors_Bucket with the vector storage feature enabled
2. THE S3_Vectors_Bucket SHALL be configured with a Vector_Index that supports 1024 dimensions (matching Amazon Titan Embeddings V2 output)
3. THE S3_Vectors_Bucket SHALL use a cosine similarity distance metric for vector search
4. THE Terraform_Configuration SHALL expose the vector index name, dimension, and distance metric as configurable variables with defaults

### Requirement 6: Bedrock Model Access

**User Story:** As a user, I want Amazon Bedrock configured for both embedding generation and LLM inference, so that the RAG pipeline can convert text to vectors and generate answers.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL configure IAM access to Amazon Titan Embeddings V2 for generating vector embeddings
2. THE Terraform_Configuration SHALL configure IAM access to Anthropic Claude via cross-region inference profile for generating answers
3. THE Terraform_Configuration SHALL expose the model identifiers as configurable variables with sensible defaults
4. WHEN the user specifies alternative model identifiers, THE Terraform_Configuration SHALL use those models instead of the defaults

### Requirement 7: Ingest Lambda

**User Story:** As a user, I want an automated ingest pipeline that fetches AWS news articles, embeds them, and stores vectors, so that the corpus stays current.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL provision an Ingest_Lambda function with Python 3.12 runtime
2. THE Ingest_Lambda SHALL be triggered on a configurable EventBridge schedule (default daily 06:00 UTC)
3. THE Ingest_Lambda SHALL be invoked during `terraform apply` for bootstrap corpus population
4. THE Ingest_Lambda SHALL have access to S3, S3 Vectors, and Bedrock embedding model
5. THE Ingest_Lambda deployment package SHALL include the shared `rag/` Python library
6. THE Ingest_Lambda SHALL have a dedicated CloudWatch log group with 14-day retention

### Requirement 8: Query Lambda

**User Story:** As a user, I want an API handler that processes questions and returns grounded answers, so that the web UI can provide a RAG experience.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL provision a Query_Lambda function with Python 3.12 runtime
2. THE Query_Lambda SHALL handle `GET /status`, `POST /query`, and `POST /ingest` routes
3. THE Query_Lambda SHALL have access to S3, S3 Vectors, Bedrock (embedding + LLM), and invoke permission on Ingest_Lambda
4. THE Query_Lambda SHALL include CORS headers matching the Amplify origin
5. THE Query_Lambda SHALL have a dedicated CloudWatch log group with 14-day retention
6. THE Query_Lambda deployment package SHALL include the shared `rag/` Python library

### Requirement 9: API Gateway

**User Story:** As a user, I want an HTTP API with JWT authentication and CORS, so that the web UI can securely communicate with the backend.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL provision an API_Gateway HTTP API with CORS configuration matching the Amplify origin
2. THE API_Gateway SHALL use a JWT authorizer backed by the Cognito_User_Pool
3. THE API_Gateway SHALL define routes: `GET /status`, `POST /query`, `POST /ingest`, plus OPTIONS preflight routes
4. THE API_Gateway SHALL use auto-deploy with configurable throttle rate and burst limits
5. THE API_Gateway SHALL grant Lambda invoke permission to the Query_Lambda

### Requirement 10: Cognito Authentication

**User Story:** As a user, I want user authentication with admin group support, so that the app is secure and admin functions are restricted.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL provision a Cognito_User_Pool with email-based usernames and auto-verified email
2. THE Cognito_User_Pool SHALL enforce a strong password policy (12+ chars, mixed case, numbers, symbols)
3. THE Terraform_Configuration SHALL provision an SPA client with SRP and password auth flows
4. THE Terraform_Configuration SHALL create an `admins` group for admin-only operations
5. WHEN `cognito_admin_email` is set, THE Terraform_Configuration SHALL create an admin user with auto-generated or specified password
6. THE Cognito client callback and logout URLs SHALL include the Amplify app URL

### Requirement 11: Amplify Hosting

**User Story:** As a user, I want a hosted web UI deployed automatically, so that I can interact with the RAG system through a browser.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL provision an Amplify_App for static SPA hosting
2. THE Amplify_App SHALL deploy the `web/` directory with runtime configuration injected from Terraform outputs
3. THE deployment SHALL use a `null_resource` with `local-exec` to build config.js and upload to Amplify
4. THE deployment SHALL re-trigger when web source files, API endpoint, or Cognito configuration changes
5. THE Amplify_App SHALL use a SPA redirect rule (404 → 200 to index.html)

### Requirement 12: CI/CD Workflows

**User Story:** As a maintainer, I want GitHub Actions workflows for linting and validation, so that code quality is enforced automatically.

#### Acceptance Criteria

1. THE CI_Workflows SHALL include a markdown-lint workflow using actionsforge/actions reusable workflows
2. THE CI_Workflows SHALL include a terraform-lint-validate workflow using actionsforge/actions reusable workflows
3. THE CI_Workflows SHALL include a commitmsg-conform workflow using actionsforge/actions reusable workflows
4. WHEN a pull request is opened or updated, THE CI_Workflows SHALL execute all checks

### Requirement 13: Single Region Deployment

**User Story:** As a user, I want all resources deployed in a single configurable AWS region, so that the demo is simple and avoids cross-region complexity.

#### Acceptance Criteria

1. THE Terraform_Configuration SHALL deploy all AWS resources within a single AWS region
2. THE Terraform_Configuration SHALL expose the AWS region as a configurable variable with a default value
3. THE Terraform_Configuration SHALL validate that the region variable matches the pattern of a valid AWS region

### Requirement 14: Steering and Documentation

**User Story:** As a developer using Kiro, I want steering files and documentation that reflect the current architecture, so that AI-assisted development follows the project's patterns.

#### Acceptance Criteria

1. THE project SHALL include a `.kiro/steering/terraform-conventions.md` file describing current Terraform coding standards
2. THE project SHALL include a `.kiro/steering/domain-context.md` file describing the full-stack RAG architecture
3. THE README SHALL describe the architecture, security model, deployment steps, and project structure
4. THE project SHALL include a LICENSE file with MIT license text and copyright attributed to John Ajera
