# Azure deployment (placeholder)

Not built yet. Implement the Azure adapters and add Terraform here. This track closes the
Microsoft-stack gap for the Avanade and Lead AI Engineer roles.

| Concern | Adapter / config | Planned Azure service |
|---|---|---|
| Object storage | `app/adapters/storage/azure.py` | Blob Storage (private endpoint) |
| Ingestion queue | `app/adapters/queue/azure.py` | Service Bus + Container Apps job |
| OCR | `app/adapters/ocr/azure.py` | Azure AI Document Intelligence |
| PII | `app/adapters/pii/azure.py` | Azure AI Language PII (or keep Presidio) |
| LLM + embeddings | `config/litellm/azure.yaml` | Azure OpenAI / AI Foundry |
| Postgres + pgvector | `DATABASE_URL` | Azure Database for PostgreSQL Flexible Server |
| Compute | Terraform | Azure Container Apps (LiteLLM sidecar) or AKS |
| Secrets | Terraform | Key Vault + managed identity |
| Observability | OpenTelemetry exporter | Azure Monitor / Application Insights |

Suggested files: `versions.tf`, `variables.tf`, `network.tf`, `postgres.tf`, `container_apps.tf`, `identity.tf`, `outputs.tf`.
