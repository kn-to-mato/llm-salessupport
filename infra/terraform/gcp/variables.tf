variable "project_id" {
  type        = string
  description = "GCP project id"
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "asia-northeast1"
}

variable "artifact_repository_id" {
  type        = string
  description = "Artifact Registry repository id (lowercase, hyphen allowed)"
  default     = "kentomax-sales-support"
}

variable "cloud_run_service_name" {
  type        = string
  description = "Cloud Run service name"
  default     = "kentomax-sales-support-backend-vertex"
}

variable "deploy_cloud_run" {
  type        = bool
  description = "Whether to create Cloud Run service (useful for two-phase apply before image push)"
  default     = false
}

variable "container_image" {
  type        = string
  description = "Container image URI to deploy (Artifact Registry recommended)"
  default     = ""
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to resources where supported"
  default = {
    please_keep_it = "true"
    # GCP label value does not allow '.' so we sanitize to hyphen.
    user = "kento-tomatsu"
    app  = "llm-salessupport"
  }
}

###############################################################################
# Datadog LLM Observability (auto instrumentation)
###############################################################################

variable "dd_site" {
  type        = string
  description = "Datadog site (e.g., datadoghq.com for US1)"
  default     = "datadoghq.com"
}

variable "dd_env" {
  type        = string
  description = "Datadog environment tag"
  default     = "dev"
}

variable "dd_service" {
  type        = string
  description = "Datadog service name (unified service tagging)"
  default     = "kentomax-sales-support-backend-vertex"
}

variable "dd_llmobs_ml_app" {
  type        = string
  description = "LLM Observability ML app name"
  default     = "python-llm-salessupport-vertex"
}

variable "dd_api_key_secret_name" {
  type        = string
  description = "Secret Manager secret name that stores DD_API_KEY"
  default     = "kento-tomax-api-key-for-log"
}

