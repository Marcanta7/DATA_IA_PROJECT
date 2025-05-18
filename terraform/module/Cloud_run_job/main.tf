resource "google_cloud_run_v2_job" "job" {
  project  = var.project_id
  location = var.region
  name     = var.job_name

  template {
    task_count = 1 # Para una ejecución única, se puede parametrizar si es necesario
    template {
      service_account = var.service_account_email
      containers {
        image = var.container_image
        resources {
          limits = {
            memory = var.memory_limit
            cpu    = var.cpu_limit
          }
        }
        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.value.name
            value = env.value.value
          }
        }
        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.value.name
            value_source {
              secret_key_ref {
                secret  = "projects/${var.project_id}/secrets/${env.value.secret_name}"
                version = env.value.secret_version
              }
            }
          }
        }
      }
      max_retries     = var.max_retries
      timeout         = "${var.task_timeout_seconds}s" # En v2 el formato es string con 's'

      dynamic "vpc_access" {
        for_each = var.vpc_connector_id != null ? [1] : []
        content {
          connector = var.vpc_connector_id
          egress    = var.vpc_egress != null ? upper(replace(var.vpc_egress, "-", "_")) : null
        }
      }
    }
  }
  # launch_stage = "BETA" # O GA si ya está disponible
}

# Para ejecutar este job, normalmente usarías gcloud CLI, la consola de GCP, o las bibliotecas cliente.
# Terraform define el job, no lo ejecuta.
# Ejemplo: gcloud run jobs execute JOB_NAME --region REGION --project PROJECT_ID --wait