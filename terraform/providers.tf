terraform {
  required_version = ">= 1.3" # Se recomienda una versión reciente

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Usa una versión reciente y fija el mayor
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

# El proveedor google-beta a veces es necesario para recursos más nuevos
provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}