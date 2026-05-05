# ─── Public Access ───────────────────────────────────────────────────────────
# Allow unauthenticated access to the Cloud Run service
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.app_project_id
  location = var.region
  name     = google_cloud_run_v2_service.studio.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── Cloud Build Deployer ────────────────────────────────────────────────────
# Allow the CI/CD service account to deploy new revisions
resource "google_cloud_run_v2_service_iam_member" "cloudbuild_deployer" {
  project  = var.app_project_id
  location = var.region
  name     = google_cloud_run_v2_service.studio.name
  role     = "roles/run.developer"
  member   = "serviceAccount:cloudbuild-deployer@${var.cicd_project_id}.iam.gserviceaccount.com"
}
