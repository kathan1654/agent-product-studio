variable "app_project_id" {
  description = "GCP project for deploying the application"
  type        = string
  default     = "gcp-app-infra-dev"
}

variable "cicd_project_id" {
  description = "GCP project for CI/CD resources"
  type        = string
  default     = "gcp-cicd-infra-auth"
}

variable "region" {
  description = "GCP region for deployment"
  type        = string
  default     = "northamerica-northeast1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "agent-product-studio"
}

variable "image_tag" {
  description = "Docker image tag for the deployment"
  type        = string
  default     = "latest"
}
