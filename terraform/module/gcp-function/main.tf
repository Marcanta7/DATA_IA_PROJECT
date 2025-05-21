resource "null_resource" "build_and_deploy_cloud_run" {
  provisioner "local-exec" {
    command = <<EOT
      # Variables
      PROJECT_ID=${var.project_id}
      REGION=${var.region}
      REPO_NAME=${var.reponame}
      SERVICE_NAME=${var.cloud_run_service_name}
      IMAGE_NAME=${var.image_name}
      IMAGE_TAG=latest
      IMAGE_URI=${var.region}-docker.pkg.dev/${var.project_id}/${var.reponame}/${var.image_name}:${IMAGE_TAG}

      # Autenticación de Docker con Artifact Registry
      gcloud auth configure-docker ${var.region}-docker.pkg.dev --quiet

      # Construir imagen desde carpeta local
      docker build -t ${IMAGE_URI} ./gcp-function

      # Subir imagen a Artifact Registry
      docker push ${IMAGE_URI}

      # Desplegar en Cloud Run
      gcloud run deploy ${SERVICE_NAME} \
        --image=${IMAGE_URI} \
        --region=${REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --project=${PROJECT_ID}
    EOT
    interpreter = ["/bin/bash", "-c"]
  }

  triggers = {
    always_run = "${timestamp()}"
  }
}