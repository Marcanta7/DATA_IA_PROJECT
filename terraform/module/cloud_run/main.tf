resource "google_cloud_run_v2_service" "service" {
  project  = var.project_id
  location = var.region
  name     = var.service_name

  template {
    service_account = var.service_account_email
    containers {
      image = var.container_image
      ports {
        container_port = var.container_port
      }
      resources {
        limits = {
          memory = var.memory
          cpu    = var.cpu
        }
      }

      # Variables de entorno directas
      dynamic "env" {
        for_each = var.env_vars
        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      # Variables de entorno desde Secret Manager
      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.value.name
          value_source {
            secret_key_ref {
              # El secreto debe estar en el mismo proyecto. Si está en otro, se necesita el path completo.
              secret  = "projects/${var.project_id}/secrets/${env.value.secret_name}"
              version = env.value.secret_version
            }
          }
        }
      }
    startup_probe {
      timeout_seconds                  = var.timeout_seconds
    }
    }

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    # container_concurrency y timeout_seconds están en el nivel superior de template en v2
    max_instance_request_concurrency = var.container_concurrency # En v2 se llama así

    # Configuración de VPC Access
    dynamic "vpc_access" {
      for_each = var.vpc_connector_id != null ? [1] : []
      content {
        connector = var.vpc_connector_id
        # La API de v2 espera el egress en mayúsculas y con guion bajo
        egress = var.vpc_egress != null ? upper(replace(var.vpc_egress, "-", "_")) : null
      }
    }
    # execution_environment = "EXECUTION_ENVIRONMENT_GEN1" # O GEN2, GEN2 es el predeterminado
  }

  # Configuración del tráfico para la última revisión
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # labels = { ... } # Puedes añadir etiquetas aquí
}

# Política IAM para permitir acceso no autenticado (público) si se especifica
resource "google_cloud_run_v2_service_iam_member" "allow_unauthenticated" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id # Asegúrate de que esto es el ID del proyecto y no el número
  location = var.region
  name     = google_cloud_run_v2_service.service.name # Referencia al nombre del servicio
  role     = "roles/run.invoker"
  member   = "allUsers"

  depends_on = [google_cloud_run_v2_service.service]
}