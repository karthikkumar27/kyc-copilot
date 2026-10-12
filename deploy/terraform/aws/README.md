# AWS deployment (placeholder)

Not built yet. The application code already supports AWS through adapters; implement these and
add Terraform here. Nothing in `app/` outside `app/adapters/*/aws.py` should need to change.

| Concern | Adapter / config | Planned AWS service |
|---|---|---|
| Object storage | `app/adapters/storage/aws.py` | S3 (SSE-KMS, block public access) |
| Ingestion queue | `app/adapters/queue/aws.py` | SQS + ECS Fargate worker (or Lambda for small docs) |
| OCR | `app/adapters/ocr/aws.py` | Amazon Textract |
| PII | `app/adapters/pii/aws.py` | Amazon Comprehend PII detection (or keep Presidio) |
| LLM + embeddings | `config/litellm/aws.yaml` | Amazon Bedrock |
| Postgres + pgvector | `DATABASE_URL` | RDS / Aurora PostgreSQL |
| Compute | Terraform | ECS Fargate (API + worker, LiteLLM sidecar) or EKS |
| Secrets | Terraform | Secrets Manager |
| Observability | OpenTelemetry exporter | CloudWatch + X-Ray |

Suggested files: `versions.tf`, `variables.tf`, `network.tf`, `rds.tf`, `ecs.tf`, `iam.tf`, `outputs.tf`.
