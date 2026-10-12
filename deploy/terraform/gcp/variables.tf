variable "project_id" {
  type = string
}

variable "region" {
  type        = string
  default     = "asia-southeast1"
  description = "Closest region to Malaysia. Check whether a Malaysian region offers every service you need."
}

variable "vertex_location" {
  type        = string
  default     = "asia-southeast1"
  description = "Where Vertex AI models are called. Model availability varies by region."
}

variable "image_tag" {
  type    = string
  default = "v0.1.0"
}

variable "db_tier" {
  type    = string
  default = "db-g1-small"
}

variable "deletion_protection" {
  type    = bool
  default = false
}

variable "pii_provider" {
  type        = string
  default     = "gcp"
  description = "gcp (Sensitive Data Protection) or presidio (in-container)."
}

variable "enable_document_ai" {
  type        = bool
  default     = false
  description = "Opt-in: Document AI processors run in limited locations (us/eu), a residency trade-off."
}

variable "document_ai_location" {
  type    = string
  default = "us"
}
