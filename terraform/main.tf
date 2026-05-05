terraform {
  backend "gcs" {
    bucket = "gcp-app-infra-dev-tfstate"
    prefix = "terraform/state/agent-product-studio"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.45.2"
    }
  }

  required_version = ">= 1.5.0"
}

provider "google" {
  project = var.app_project_id
  region  = var.region
}
