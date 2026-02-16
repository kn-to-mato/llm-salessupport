output "artifact_registry_repo" {
  value       = google_artifact_registry_repository.repo.name
  description = "Artifact Registry repository resource name"
}

output "cloud_run_url" {
  value       = var.deploy_cloud_run ? google_cloud_run_v2_service.backend[0].uri : null
  description = "Cloud Run service URL"
}

