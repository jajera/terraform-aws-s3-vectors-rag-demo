# Implementation Plan: S3 Vectors RAG Demo

## Overview

This plan reflects the current implemented state of the cloud-native AWS announcements briefing demo. All tasks are completed. The system provisions S3, S3 Vectors, Lambda (ingest + query), API Gateway, Cognito, and Amplify via Terraform, with a Python RAG library and static web UI.

## Tasks

- [x] 1. Set up foundational Terraform configuration
  - [x] 1.1 Create `versions.tf` with Terraform and provider version constraints
    - Define `required_version = ">= 1.5.0"`
    - Add AWS provider `hashicorp/aws` with version `>= 6.24.0`
    - Add random, archive, and null providers
    - _Requirements: 1.3_

  - [x] 1.2 Create `variables.tf` with all input variables and validation blocks
    - Define all infrastructure, model, Cognito, and API throttle variables
    - Include validation blocks and sensitive markers where applicable
    - _Requirements: 1.5, 2.4, 5.4, 6.3, 13.2, 13.3_

  - [x] 1.3 Create `providers.tf` with AWS provider configuration and default_tags
    - Configure AWS provider with `region = var.aws_region`
    - Add `default_tags` block with Project, Environment, and ManagedBy tags
    - _Requirements: 1.4, 2.1, 2.2, 2.3, 13.1_

  - [x] 1.4 Create `main.tf` with shared locals
    - Define random_id for bucket prefix
    - Define locals for bucket names and Amplify origin
    - _Requirements: 4.1_

  - [x] 1.5 Create `terraform.tfvars` with user-configurable values
    - Set all variables with `# REPLACE` comments
    - _Requirements: 1.7_

  - [x] 1.6 Create `data.tf` with data sources
    - Add `aws_caller_identity` and `aws_region` data sources
    - _Requirements: 3.2_

- [x] 2. Implement S3 and S3 Vectors resources
  - [x] 2.1 Create `s3.tf` with source documents bucket
    - S3 bucket with force_destroy, versioning, encryption, TLS policy
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 3.5_

  - [x] 2.2 Create `s3_vectors.tf` with vector bucket and index
    - S3 Vectors bucket and index with configurable dimension/metric
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 3. Implement Lambda functions
  - [x] 3.1 Create `lambda_ingest.tf` with ingest Lambda, IAM, and schedule
    - Archive file, IAM role/policy, Lambda function, CloudWatch logs
    - EventBridge schedule, bootstrap invocation, permissions
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 3.3_

  - [x] 3.2 Create `lambda_query.tf` with query Lambda and IAM
    - Archive file, IAM role/policy, Lambda function, CloudWatch logs
    - API Gateway permission
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 3.4_

- [x] 4. Implement authentication and API
  - [x] 4.1 Create `cognito.tf` with user pool and admin setup
    - User pool, SPA client, domain, admin group, optional admin user
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x] 4.2 Create `api_gateway.tf` with HTTP API and JWT auth
    - HTTP API, Cognito authorizer, routes, integrations, stage
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 3.6, 3.7, 3.8_

- [x] 5. Implement Amplify hosting
  - [x] 5.1 Create `amplify.tf` with app, branch, and deploy provisioner
    - Amplify app, main branch, null_resource deploy
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 6. Implement outputs and support files
  - [x] 6.1 Create `outputs.tf` with all output values
    - App URL, API endpoint, Cognito, buckets, Lambda, model IDs
    - _Requirements: 1.6_

  - [x] 6.2 Create `random.tf` with Cognito password generation
    - random_password for auto-generated admin credentials
    - _Requirements: 10.5_

  - [x] 6.3 Create `iam.tf` with shared locals
    - Foundation model ID local for cross-region inference profile
    - _Requirements: 6.2_

  - [x] 6.4 Create `.gitignore`
    - Terraform, Python, build artifacts, corpus files
    - _Requirements: 1.8_

- [x] 7. Implement Python RAG library
  - [x] 7.1 Create `rag/` package with config, fetch, ingest, and query modules
    - config.py, fetch.py, ingest.py, query.py, __init__.py, __main__.py
    - _Requirements: 7.1, 8.1_

  - [x] 7.2 Create `lambda/ingest/handler.py` and `lambda/query/handler.py`
    - Lambda handlers importing shared rag library
    - _Requirements: 7.1, 8.1, 8.2_

- [x] 8. Implement web UI
  - [x] 8.1 Create `web/` static SPA files
    - index.html, styles.css, config.template.js, auth.js, api.js, app.js
    - _Requirements: 11.2_

  - [x] 8.2 Create `scripts/deploy-web.sh`
    - Config injection and Amplify upload script
    - _Requirements: 11.3_

- [x] 9. Create CI workflows and documentation
  - [x] 9.1 Create `.github/workflows/` CI files
    - markdown-lint, terraform-lint-validate, commitmsg-conform
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [x] 9.2 Create steering files
    - terraform-conventions.md, domain-context.md
    - _Requirements: 14.1, 14.2_

  - [x] 9.3 Create README.md
    - Architecture, security model, deploy steps, outputs, project structure
    - _Requirements: 14.3_

## Notes

- All tasks are completed — this document reflects the implemented state
- The project uses AWS provider >= 6.24.0 (required for aws_s3vectors_* resources)
- Additional providers: random (bucket prefix), archive (Lambda zips), null (Amplify deploy)
- Property-based tests are not applicable to this IaC + thin-Lambda project
- Testing is handled via CI workflows and post-apply integration testing

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "1.5", "1.6"] },
    { "id": 2, "tasks": ["2.1", "2.2"] },
    { "id": 3, "tasks": ["3.1", "3.2"] },
    { "id": 4, "tasks": ["4.1", "4.2"] },
    { "id": 5, "tasks": ["5.1"] },
    { "id": 6, "tasks": ["6.1", "6.2", "6.3", "6.4"] },
    { "id": 7, "tasks": ["7.1", "7.2"] },
    { "id": 8, "tasks": ["8.1", "8.2"] },
    { "id": 9, "tasks": ["9.1", "9.2", "9.3"] }
  ]
}
```
