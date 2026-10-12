# Each Cloud Run service runs the app container plus a LiteLLM sidecar on localhost:4000.
# The API is NOT public: grant roles/run.invoker to your own user and call it through
# `gcloud run services proxy kyc-api --region <region>` until OIDC auth lands.

resource "google_cloud_run_v2_service" "worker" {
  name                = "kyc-worker"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL" # IAM-protected; Cloud Tasks needs to reach it
  deletion_protection = false

  template {
    service_account = google_service_account.worker.email
    timeout         = "900s"
    scaling {
      max_instance_count = 3
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }

    containers {
      name       = "worker"
      image      = local.app_image
      command    = ["uvicorn"]
      args       = ["app.worker_http:app", "--host", "0.0.0.0", "--port", "8080"]
      depends_on = ["litellm"]
      ports {
        container_port = 8080
      }
      resources {
        limits = { cpu = "2", memory = "2Gi" }
      }
      dynamic "env" {
        for_each = local.app_env
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "LLM_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_key.secret_id
            version = "latest"
          }
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    containers {
      name  = "litellm"
      image = local.litellm_image
      args  = ["--config", "/app/config.yaml", "--port", "4000"]
      resources {
        limits = { cpu = "1", memory = "1Gi" }
      }
      startup_probe {
        tcp_socket {
          port = 4000
        }
        period_seconds    = 5
        failure_threshold = 24
      }
      dynamic "env" {
        for_each = local.litellm_env
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name = "LITELLM_MASTER_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
  depends_on = [google_project_iam_member.runtime, google_secret_manager_secret_iam_member.db_password,
                google_secret_manager_secret_iam_member.litellm_key]
}

resource "google_cloud_run_v2_service" "api" {
  name                = "kyc-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.api.email
    scaling {
      max_instance_count = 3
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }

    containers {
      name       = "api"
      image      = local.app_image
      command    = ["uvicorn"]
      args       = ["app.main:app", "--host", "0.0.0.0", "--port", "8080"]
      depends_on = ["litellm"]
      ports {
        container_port = 8080
      }
      resources {
        limits = { cpu = "1", memory = "2Gi" }
      }
      dynamic "env" {
        for_each = merge(local.app_env, {
          WORKER_URL            = google_cloud_run_v2_service.worker.uri
          TASKS_SERVICE_ACCOUNT = google_service_account.api.email
        })
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "LLM_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_key.secret_id
            version = "latest"
          }
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      startup_probe {
        http_get {
          path = "/healthz"
        }
        period_seconds    = 5
        failure_threshold = 24
      }
    }

    containers {
      name  = "litellm"
      image = local.litellm_image
      args  = ["--config", "/app/config.yaml", "--port", "4000"]
      resources {
        limits = { cpu = "1", memory = "1Gi" }
      }
      startup_probe {
        tcp_socket {
          port = 4000
        }
        period_seconds    = 5
        failure_threshold = 24
      }
      dynamic "env" {
        for_each = local.litellm_env
        content {
          name  = env.key
          value = env.value
        }
      }
      env {
        name = "LITELLM_MASTER_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }
  depends_on = [google_project_iam_member.runtime, google_secret_manager_secret_iam_member.db_password,
                google_secret_manager_secret_iam_member.litellm_key]
}

# Run with: gcloud run jobs execute kyc-migrate --region <region> --wait
resource "google_cloud_run_v2_job" "migrate" {
  name                = "kyc-migrate"
  location            = var.region
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.api.email
      max_retries     = 1
      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.main.connection_name]
        }
      }
      containers {
        image   = local.app_image
        command = ["alembic"]
        args    = ["upgrade", "head"]
        dynamic "env" {
          for_each = {
            DB_USER = google_sql_user.app.name, DB_NAME = google_sql_database.app.name,
            DB_SOCKET_DIR = local.cloudsql_dir
          }
          content {
            name  = env.key
            value = env.value
          }
        }
        env {
          name = "DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.db_password.secret_id
              version = "latest"
            }
          }
        }
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }
  depends_on = [google_project_iam_member.runtime, google_secret_manager_secret_iam_member.db_password]
}
