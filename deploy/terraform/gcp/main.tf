locals {
  services = [
    "run.googleapis.com", "sqladmin.googleapis.com", "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com", "cloudtasks.googleapis.com", "aiplatform.googleapis.com",
    "dlp.googleapis.com", "storage.googleapis.com", "iam.googleapis.com",
    "documentai.googleapis.com",
  ]
  registry      = "${var.region}-docker.pkg.dev/${var.project_id}/kyc"
  app_image     = "${local.registry}/app:${var.image_tag}"
  litellm_image = "${local.registry}/litellm:${var.image_tag}"
  cloudsql_dir  = "/cloudsql/${google_sql_database_instance.main.connection_name}"

  # Shared app configuration. Secrets are injected separately from Secret Manager.
  app_env = {
    ENVIRONMENT      = "staging"
    AUTH_MODE        = "dev" # protected by Cloud Run IAM until OIDC lands (week 4)
    DEFAULT_TENANT   = "limaupay"
    DB_USER          = google_sql_user.app.name
    DB_NAME          = google_sql_database.app.name
    DB_SOCKET_DIR    = local.cloudsql_dir
    LLM_BASE_URL     = "http://localhost:4000/v1" # LiteLLM sidecar in the same instance
    STORAGE_PROVIDER = "gcp"
    QUEUE_PROVIDER   = "gcp"
    OCR_PROVIDER     = var.enable_document_ai ? "gcp" : "local"
    PII_PROVIDER     = var.pii_provider
    GCP_PROJECT      = var.project_id
    GCP_REGION       = var.region
    GCS_BUCKET       = google_storage_bucket.docs.name
    DLP_LOCATION     = var.region
    DOCAI_LOCATION   = var.document_ai_location
    DOCAI_PROCESSOR_ID = try(reverse(split("/", google_document_ai_processor.ocr[0].name))[0], "")
    TASKS_LOCATION   = var.region
    TASKS_QUEUE      = google_cloud_tasks_queue.ingest.name
  }

  litellm_env = {
    GCP_PROJECT     = var.project_id
    VERTEX_LOCATION = var.vertex_location
  }
}

resource "google_project_service" "enabled" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}

# ---------------- Registry, storage, secrets ----------------
resource "google_artifact_registry_repository" "kyc" {
  location      = var.region
  repository_id = "kyc"
  format        = "DOCKER"
  depends_on    = [google_project_service.enabled]
}

resource "google_storage_bucket" "docs" {
  name                        = "${var.project_id}-kyc-docs"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = !var.deletion_protection
  versioning {
    enabled = true
  }
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "random_password" "litellm" {
  length  = 40
  special = false
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "kyc-db-password"
  replication {
    auto {}
  }
  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db.result
}

resource "google_secret_manager_secret" "litellm_key" {
  secret_id = "kyc-litellm-master-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "litellm_key" {
  secret      = google_secret_manager_secret.litellm_key.id
  secret_data = "sk-${random_password.litellm.result}"
}

# ---------------- Cloud SQL (Postgres + pgvector) ----------------
resource "google_sql_database_instance" "main" {
  name                = "kyc-pg"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.db_tier
    edition           = "ENTERPRISE"
    availability_type = "ZONAL" # use REGIONAL for real production HA
    ip_configuration {
      ipv4_enabled = true # no authorized networks: access only via the IAM-checked Cloud SQL connector
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }
  depends_on = [google_project_service.enabled]
}

resource "google_sql_database" "app" {
  name     = "kyc"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  name     = "kyc"
  instance = google_sql_database_instance.main.name
  password = random_password.db.result
}

# ---------------- Optional Document AI ----------------
resource "google_document_ai_processor" "ocr" {
  count        = var.enable_document_ai ? 1 : 0
  location     = var.document_ai_location
  display_name = "kyc-ocr"
  type         = "OCR_PROCESSOR"
  depends_on   = [google_project_service.enabled]
}

# ---------------- Queue ----------------
resource "google_cloud_tasks_queue" "ingest" {
  name     = "kyc-ingest"
  location = var.region
  retry_config {
    max_attempts  = 5
    min_backoff   = "10s"
    max_backoff   = "300s"
  }
  rate_limits {
    max_concurrent_dispatches = 5
  }
  depends_on = [google_project_service.enabled]
}
