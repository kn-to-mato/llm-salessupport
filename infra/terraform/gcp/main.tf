provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  services = toset([
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "aiplatform.googleapis.com",
    "secretmanager.googleapis.com",
  ])
}

resource "google_project_service" "services" {
  for_each           = local.services
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

