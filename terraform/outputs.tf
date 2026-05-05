# ─── Outputs ─────────────────────────────────────────────────────────────────
output "app_url" {
  description = "URL of the deployed Agent Product Studio"
  value       = google_cloud_run_v2_service.studio.uri
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.studio.name
}

output "image_path" {
  description = "Full path to the container image in Artifact Registry"
  value       = "${var.region}-docker.pkg.dev/${var.app_project_id}/policing-dashboard/${var.service_name}:${var.image_tag}"
}
