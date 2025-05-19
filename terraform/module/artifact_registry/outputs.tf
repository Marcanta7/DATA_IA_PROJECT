output "repository_ids" {
  description = "IDs de los repositorios de Artifact Registry creados."
  value       = { for k, repo in google_artifact_registry_repository.repos : k => repo.repository_id }
}

output "repository_names" {
  description = "Nombres completos de los repositorios de Artifact Registry."
  value       = { for k, repo in google_artifact_registry_repository.repos : k => repo.name }
}

output "repositories_details" {
  description = "Detalles de los repositorios de Artifact Registry creados, incluyendo la URL."
  value = {
    for k, repo in google_artifact_registry_repository.repos : k => {
      id   = repo.repository_id
      name = repo.name
      url  = "${var.region}-docker.pkg.dev/${var.project_id}/${repo.repository_id}"
    }
  }
}