# Terraform Conventions

This document describes the Terraform coding standards for this project. Follow these conventions when generating or modifying infrastructure code.

## Flat Structure

- All `.tf` files live in the repository root. Do not create nested directories such as `modules/`, `environments/`, or `stacks/`.
- Group related resources into a single file named after the primary concern (e.g., `s3.tf`, `cognito.tf`, `api_gateway.tf`, `lambda_ingest.tf`).
- Use dedicated files for concerns: `versions.tf` (version constraints), `providers.tf` (provider config + default_tags), `main.tf` (locals and shared config), `variables.tf` (all input variables), `outputs.tf` (all outputs), `data.tf` (data sources).

## Naming Conventions

- Use `snake_case` for all Terraform identifiers: resource names, variable names, output names, data source names, and local values.
- Resource logical names should be descriptive and concise (e.g., `aws_s3_bucket.source_documents`, `aws_lambda_function.ingest`, `aws_cognito_user_pool.main`).
- Variable names should clearly describe their purpose without redundant prefixes.

## Tagging Standard

- Apply three mandatory tags to every taggable AWS resource: `Project`, `Environment`, and `ManagedBy`.
- Use `default_tags` in the AWS provider block to apply tags globally rather than repeating them on each resource.
- `ManagedBy` is always set to `"Terraform"`.
- `Project` and `Environment` are driven by input variables.

## Variable Validation

- Every variable must include a `validation` block with a meaningful `error_message`.
- Use `can(regex(...))` for pattern-based string validation (e.g., AWS region format).
- Use `contains([...], var.x)` for enum-style constraints.
- Use `length()` checks for string length bounds.
- Use numeric comparisons for range constraints on number variables.
- Sensitive variables (e.g., `cognito_admin_email`, `cognito_admin_password`) use `sensitive = true`.

## Resource-per-File Grouping

- Place each logical group of related resources in its own file:
  - `s3.tf` — S3 bucket, versioning, encryption, bucket policy
  - `s3_vectors.tf` — S3 Vectors bucket and vector index
  - `cognito.tf` — Cognito user pool, client, domain, groups, users
  - `api_gateway.tf` — HTTP API, authorizer, routes, integrations, stage
  - `lambda_ingest.tf` — Ingest Lambda function, IAM role/policy, EventBridge schedule, CloudWatch logs
  - `lambda_query.tf` — Query Lambda function, IAM role/policy, API Gateway permission, CloudWatch logs
  - `amplify.tf` — Amplify app, branch, deploy provisioner
  - `random.tf` — Random resources (password generation, bucket prefix)
  - `data.tf` — All data sources (caller identity, region, archive files)
- Supporting resources (e.g., bucket policy, Lambda permissions) belong in the same file as their parent resource.

## Additional Conventions

- Use `jsonencode()` for inline IAM policies rather than separate JSON files.
- Rely on environment variables or AWS credential files for authentication; never hardcode credentials.
- Use `# REPLACE` comments in `terraform.tfvars` to mark values users should customize.
- Pin the AWS provider version with `>= 6.24.0` (required for S3 Vectors support) and set `required_version >= 1.5.0`.
- Use `random_id` for globally unique bucket names to avoid conflicts.
- Use `archive_file` data sources for Lambda deployment packages.
- Use `null_resource` with `local-exec` provisioners for Amplify deployments.
- Lambda IAM roles use per-function least-privilege: separate roles for ingest and query functions.
