output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "worker_url" {
  value = google_cloud_run_v2_service.worker.uri
}

output "artifact_registry" {
  value = local.registry
}

output "docs_bucket" {
  value = google_storage_bucket.docs.name
}
