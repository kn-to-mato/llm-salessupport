resource "google_cloud_run_v2_service" "backend" {
  count = var.deploy_cloud_run ? 1 : 0

  name     = var.cloud_run_service_name
  location = var.region
  project  = var.project_id

  labels = var.labels

  template {
    service_account = google_service_account.cloud_run_sa.email

    containers {
      image = var.container_image

      env {
        name  = "VERTEX_ENABLED"
        value = "true"
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }

      env {
        name  = "VERTEX_MODEL"
        value = "gemini-2.5-flash"
      }

      env {
        name  = "CORS_ORIGINS"
        value = "http://localhost:5173,http://localhost:5174"
      }

      # Datadog LLM Observability (auto instrumentation via ddtrace-run)
      env {
        name  = "DD_SITE"
        value = var.dd_site
      }

      env {
        name  = "DD_ENV"
        value = var.dd_env
      }

      env {
        name  = "DD_SERVICE"
        value = var.dd_service
      }

      env {
        name  = "DD_LLMOBS_ENABLED"
        value = "1"
      }

      env {
        name  = "DD_LLMOBS_AGENTLESS_ENABLED"
        value = "1"
      }

      env {
        name  = "DD_LLMOBS_ML_APP"
        value = var.dd_llmobs_ml_app
      }

      env {
        name = "DD_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.dd_api_key_secret_name
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8080
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.services,
    google_project_iam_member.vertex_user,
  ]
}

# Public access (demo). Tighten later if needed.
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.deploy_cloud_run ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

