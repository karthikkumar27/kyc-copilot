terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  # Use a GCS backend for shared state, e.g.:
  # backend "gcs" { bucket = "<your-tf-state-bucket>"  prefix = "kyc-copilot" }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
