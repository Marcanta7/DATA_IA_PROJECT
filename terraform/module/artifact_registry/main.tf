resource "google_artifact_registry_repository" "repos" {
  for_each      = var.repositories
  project       = var.project_id
  location      = var.region
  repository_id = var.reponame 
  format        = "DOCKER"
}