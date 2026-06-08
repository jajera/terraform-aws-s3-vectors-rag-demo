# Domain Context: S3 Vectors RAG Briefing App

This document describes the AWS services, architecture, and RAG concepts used in this
project. The demo is a cloud-native **AWS announcements briefing** application: live RSS
ingest, S3 Vectors retrieval, Bedrock answers, Cognito authentication, API Gateway, and
an Amplify-hosted web UI.

## Application Architecture

```text
Browser → Cognito (JWT auth) → API Gateway HTTP API → Query Lambda → S3 Vectors + Bedrock
                                                    → Ingest Lambda (admin only)
EventBridge (daily cron) → Ingest Lambda → RSS feeds → S3 + S3 Vectors
Amplify Hosting → Static SPA (web/)
```

### Key Components

| Component | Purpose | Terraform file |
|-----------|---------|----------------|
| S3 Bucket | Source document storage (RSS articles as .txt) | `s3.tf` |
| S3 Vectors | Vector embeddings for similarity search | `s3_vectors.tf` |
| Ingest Lambda | Fetches RSS, embeds articles, stores vectors | `lambda_ingest.tf` |
| Query Lambda | API handler: embed question, search, generate answer | `lambda_query.tf` |
| API Gateway | HTTP API with JWT authorizer, CORS, throttling | `api_gateway.tf` |
| Cognito | User pool, SPA client, admin group | `cognito.tf` |
| Amplify | Static SPA hosting with config injection | `amplify.tf` |
| EventBridge | Daily scheduled corpus ingest | `lambda_ingest.tf` |

## Amazon S3 Vectors

Amazon S3 Vectors is a purpose-built vector storage capability within S3 that enables
similarity search over embeddings without managing a separate vector database.

### Key Concepts

- **Vector Bucket** — A specialized S3 bucket type (`aws_s3vectors_vector_bucket`) that hosts vector indexes.
- **Vector Index** — A named index (`aws_s3vectors_index`) with fixed dimension (1024), distance metric (cosine), and data type (float32).
- **Vector Operations** — `PutVectors`, `QueryVectors`, `GetVectors`, `DeleteVectors`, `ListIndexes`.

### Terraform Resources

```hcl
aws_s3vectors_vector_bucket  # Creates the vector bucket (requires AWS provider >= 6.24.0)
aws_s3vectors_index          # Creates an index with dimension, metric, and data type
```

## Amazon Bedrock

### Embedding Model (Amazon Titan Embeddings V2)

- Model ID: `amazon.titan-embed-text-v2:0`
- Purpose: Converts text into 1024-dimensional vector representations
- Used by: Both ingest and query Lambdas

### LLM (Anthropic Claude via Cross-Region Inference Profile)

- Model ID: `au.anthropic.claude-sonnet-4-5-20250929-v1:0` (AU inference profile for ap-southeast-2)
- Foundation model: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- Purpose: Generates natural language answers from retrieved context
- IAM: Requires permissions on both the inference profile ARN and underlying foundation model ARNs

### IAM Permissions

```text
# Embedding model (standard foundation model ARN)
arn:aws:bedrock:{region}::foundation-model/{embedding_model_id}

# LLM via inference profile (account-scoped)
arn:aws:bedrock:{region}:{account_id}:inference-profile/{inference_profile_id}

# Underlying foundation models for cross-region routing
arn:aws:bedrock:{region}::foundation-model/{foundation_model_id}
```

## RAG Pipeline

### Ingest Phase (Lambda)

1. Fetch AWS What's New + AWS News Blog RSS feeds
2. Parse articles, extract text, truncate to 8000 chars
3. Upload each article as `.txt` to S3 source bucket
4. Embed article body via Titan Embeddings V2 → 1024-dim vector
5. PutVectors to S3 Vectors with metadata (title, URL, published date, feed)
6. Write `.last-ingest` marker to S3

### Query Phase (Lambda)

1. Embed user question via Titan Embeddings V2
2. QueryVectors from S3 Vectors (Top-K with retrieval multiplier)
3. Load full document bodies from S3
4. Score candidates: 80% similarity + 20% recency
5. Build context from top snippets
6. Generate structured answer via Claude (Direct answer, What is known, Sources)

### Triggers

| Trigger | Lambda | When |
|---------|--------|------|
| `terraform apply` | Ingest | Bootstrap via `aws_lambda_invocation` |
| EventBridge cron | Ingest | Daily 06:00 UTC |
| `POST /ingest` | Query → Ingest (async) | Admin-only API endpoint |
| `POST /query` | Query | Any authenticated user |
| `GET /status` | Query | Any authenticated user |

## Security Model

- **Cognito JWT** on every authenticated API route
- **Admin group** (`admins`) required for `POST /ingest`
- **Separate IAM roles** per Lambda with minimum required permissions
- **TLS enforcement** via S3 bucket policy (deny insecure transport)
- **API throttling** configurable rate/burst limits
- **No public Lambda invoke** — only EventBridge and authenticated API

## Python Library (`rag/`)

Shared across both Lambdas (bundled into zip at build time):

- `config.py` — Environment-based configuration dataclass
- `fetch.py` — RSS feed fetching, HTML stripping, article parsing
- `ingest.py` — S3 upload, Bedrock embedding, S3 Vectors storage
- `query.py` — Embedding, retrieval, reranking, LLM generation

## Web UI (`web/`)

Static SPA deployed to Amplify:

- `config.template.js` — Placeholders replaced at deploy time with Terraform outputs
- `auth.js` — Cognito SRP authentication (no SDK, pure fetch)
- `api.js` — Authenticated API calls to Gateway
- `app.js` — UI logic, markdown rendering, source display
- `index.html` + `styles.css` — Layout and styling
