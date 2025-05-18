resource "google_artifact_registry_repository" "repos" {
  for_each      = var.repositories
  project       = var.project_id
  location      = var.region
  repository_id = "${var.app_prefix}-${each.value}" # ej: ai-diet-dev-ai-agent-repo
  description   = "Repositorio Docker para el servicio ${each.key} de ${var.app_prefix}"
  format        = "DOCKER"

  labels = {
    environment = split("-", var.app_prefix)[length(split("-", var.app_prefix)) - 1] # Extrae env del app_prefix
    app         = join("-", slice(split("-", var.app_prefix), 0, length(split("-", var.app_prefix)) - 1)) # Extrae nombre de app
  }
}