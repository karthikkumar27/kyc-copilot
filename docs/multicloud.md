# Multi-cloud design

One repo, one container image, one codebase. Only adapters and infrastructure differ per cloud.

## Adapter status

| Adapter | local | GCP | AWS | Azure |
|---|---|---|---|---|
| Storage | ✅ filesystem | ✅ Cloud Storage | ⏳ S3 | ⏳ Blob Storage |
| Queue | ✅ arq + Redis | ✅ Cloud Tasks | ⏳ SQS | ⏳ Service Bus |
| OCR | ✅ Tesseract (eng+msa) | ✅ Document AI (opt-in) | ⏳ Textract | ⏳ Document Intelligence |
| PII | ✅ Presidio / regex | ✅ Sensitive Data Protection | ⏳ Comprehend | ⏳ AI Language |
| LLM gateway | ✅ LiteLLM (Gemini API) | ✅ LiteLLM (Vertex AI) | ⏳ Bedrock config | ⏳ Azure OpenAI config |
| Infra | ✅ Docker Compose | ✅ Terraform | ⏳ | ⏳ |

✅ implemented · ⏳ placeholder (registered, fails fast at startup with a clear message)

## Adding a provider

1. Implement the Protocol in `app/adapters/<kind>/base.py` in `app/adapters/<kind>/<cloud>.py`.
   The constructor receives `Settings`; validate required settings there so misconfiguration
   fails at startup.
2. It is already registered in `app/adapters/registry.py`; replace the `PlannedProvider` base.
3. Add the SDK to the matching extra in `pyproject.toml` (`aws` or `azure`).
4. Add a contract test that runs the same checks against every implementation.
5. Fill in `config/litellm/<cloud>.yaml` and `deploy/terraform/<cloud>/`.

## Things that stay identical everywhere

The API, RAG pipeline, prompts, disclosure policy, Postgres schema (pgvector + full-text),
evaluation suite and governance artefacts. That is the point: you evaluate once and deploy anywhere.
