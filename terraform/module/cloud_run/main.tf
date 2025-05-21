resource "google_cloud_run_service" "service_agent" {
  name     = "diet-agent"
  location = "europe-west1"  # o donde esté tu servicio

  template {
    spec {
      containers {
        image = "gcr.io/diap3-458416/diet-agent@sha256:bc73f87c08c32627cb4336d8ca06412a01b6808ffad8ed4301f762d598535a11"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Política IAM para permitir acceso no autenticado (público) si se especifica
resource "google_cloud_run_v2_service_iam_member" "allow_unauthenticated_agent" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id 
  location = var.region
  name     = google_cloud_run_service.service_agent.name 
  role     = "roles/run.invoker"
  member   = "allUsers"

  depends_on = [google_cloud_run_service.service_agent]
}