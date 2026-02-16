resource "google_service_account" "cloud_run_sa" {
  project      = var.project_id
  account_id   = "kentomax-sales-support-cr"
  display_name = "kentomax sales support Cloud Run SA"
}

# Cloud Run service agent needs to be able to pull images from Artifact Registry
data "google_project" "current" {
  project_id = var.project_id
}

locals {
  cloud_run_service_agent = "serviceAccount:service-${data.google_project.current.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_artifact_registry_repository_iam_member" "cloud_run_repo_reader" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.repo.repository_id
  role       = "roles/artifactregistry.reader"
  member     = local.cloud_run_service_agent

  depends_on = [google_project_service.services, google_artifact_registry_repository.repo]
}

# Allow the Cloud Run runtime SA to call Vertex AI
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_iam_member" "dd_api_key_accessor" {
  project   = var.project_id
  secret_id = var.dd_api_key_secret_name
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"

  depends_on = [google_project_service.services]
}

