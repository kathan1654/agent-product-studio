# ─── Cloud Run Service ───────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "studio" {
  name     = var.service_name
  location = var.region
  project  = var.app_project_id

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.app_project_id}/policing-dashboard/${var.service_name}:${var.image_tag}"

      ports {
        container_port = 8501
      }

      # Environment variables for the agent framework
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.app_project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.app_project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GCP_CICD_PROJECT_ID"
        value = var.cicd_project_id
      }
      env {
        name  = "AGENT_WORKSPACE_BUCKET"
        value = "agent-product-studio"
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      # Longer startup for model initialization
      startup_probe {
        http_get {
          path = "/_stcore/health"
          port = 8501
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 5
        timeout_seconds       = 5
      }
    }

    # Use default compute service account (has Vertex AI + GCS + BQ permissions)
    service_account = "${var.app_project_id}@appspot.gserviceaccount.com"

    # Longer timeout for agent operations
    timeout = "900s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}
