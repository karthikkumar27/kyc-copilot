# Least privilege: one service account per workload.
resource "google_service_account" "api" {
  account_id   = "kyc-api"
  display_name = "KYC Copilot API"
}

resource "google_service_account" "worker" {
  account_id   = "kyc-worker"
  display_name = "KYC Copilot ingestion worker"
}

locals {
  runtime_sas = {
    api    = google_service_account.api.email
    worker = google_service_account.worker.email
  }
  # Roles both workloads need (LiteLLM sidecar calls Vertex AI as the service account).
  shared_roles = ["roles/cloudsql.client", "roles/aiplatform.user", "roles/dlp.user"]
  role_bindings = merge(
    { for pair in setproduct(keys(local.runtime_sas), local.shared_roles) :
      "${pair[0]}-${pair[1]}" => { sa = local.runtime_sas[pair[0]], role = pair[1] } },
    {
      "api-tasks"        = { sa = google_service_account.api.email, role = "roles/cloudtasks.enqueuer" }
      "worker-documentai" = { sa = google_service_account.worker.email, role = "roles/documentai.apiUser" }
    }
  )
}

resource "google_project_iam_member" "runtime" {
  for_each = local.role_bindings
  project  = var.project_id
  role     = each.value.role
  member   = "serviceAccount:${each.value.sa}"
}

resource "google_storage_bucket_iam_member" "docs" {
  for_each = local.runtime_sas
  bucket   = google_storage_bucket.docs.name
  role     = "roles/storage.objectAdmin"
  member   = "serviceAccount:${each.value}"
}

resource "google_secret_manager_secret_iam_member" "db_password" {
  for_each  = local.runtime_sas
  secret_id = google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

resource "google_secret_manager_secret_iam_member" "litellm_key" {
  for_each  = local.runtime_sas
  secret_id = google_secret_manager_secret.litellm_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value}"
}

# The API signs Cloud Tasks OIDC tokens as itself, so it needs actAs on its own account.
resource "google_service_account_iam_member" "api_act_as_self" {
  service_account_id = google_service_account.api.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.api.email}"
}

# Only the API (via Cloud Tasks) may invoke the worker.
resource "google_cloud_run_v2_service_iam_member" "worker_invoker" {
  name     = google_cloud_run_v2_service.worker.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api.email}"
}
