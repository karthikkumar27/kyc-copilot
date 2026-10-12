# GCP deployment

Cloud Run (API + ingestion worker, each with a LiteLLM sidecar), Cloud SQL Postgres 16 with
pgvector, Cloud Storage, Cloud Tasks, Secret Manager, Vertex AI and Sensitive Data Protection.

## First deploy

```bash
cd deploy/terraform/gcp
cp terraform.tfvars.example terraform.tfvars   # set project_id
terraform init

# 1. Create the registry first so there is somewhere to push images
terraform apply -target=google_project_service.enabled -target=google_artifact_registry_repository.kyc

# 2. Build and push both images (from the repo root)
gcloud auth configure-docker asia-southeast1-docker.pkg.dev
make gcp-push PROJECT=<project_id> REGION=asia-southeast1 TAG=v0.1.0

# 3. Create everything else, then run migrations
terraform apply
gcloud run jobs execute kyc-migrate --region asia-southeast1 --wait

# 4. The API is private. Grant yourself access and open a local proxy
gcloud run services add-iam-policy-binding kyc-api --region asia-southeast1 \
  --member="user:<you@example.com>" --role="roles/run.invoker"
gcloud run services proxy kyc-api --region asia-southeast1 --port 8080
python scripts/seed.py --api-url http://localhost:8080
```

## Design notes

- **No public endpoints yet.** Both services require Cloud Run IAM. AUTH_MODE=dev headers are only
  reachable by principals you have granted run.invoker. OIDC replaces this in week 4.
- **LiteLLM as a sidecar** avoids a separate service and its auth hop. Move it to a shared
  service with its own database when you need cross-instance budgets and virtual keys.
- **Residency.** Region defaults to asia-southeast1. Document AI is opt-in because its processors
  run in a few multi-regions; local Tesseract keeps documents in-region by default.
- **Cost.** Cloud Run scales to zero; Cloud SQL is the main always-on cost. Stop the instance
  (`gcloud sql instances patch kyc-pg --activation-policy=NEVER`) when you are not working.
