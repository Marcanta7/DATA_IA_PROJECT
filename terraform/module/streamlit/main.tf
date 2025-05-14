provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_artifact_registry_repository" "repo" {
  format   = "DOCKER"
  location = var.gcp_region
  repository_id = "artifact-repo-streamlit"
  description   = "Docker repo for Streamlit app"
}

resource "null_resource" "build_and_push_docker_streamlit" {
  depends_on = [google_artifact_registry_repository.repo_streamlit]

  provisioner "local-exec" {
    working_dir = path.module
    command = <<-EOT
      docker build --platform=linux/amd64 -t ${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.repo.repository_id}/${var.image_name_streamlit}:latest .
      docker push ${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.repo.repository_id}/${var.image_name_streamlit}:latest
    EOT
  }
}