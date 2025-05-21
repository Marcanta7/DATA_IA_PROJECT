variable "project_id" {
  description = "El ID del proyecto de GCP donde se desplegarán los recursos."
  type        = string
}

variable "region" {
  description = "La región de GCP para el despliegue de recursos."
  type        = string
  default     = "europe-west1" # Ejemplo, ajústalo a tu región preferida
}

variable "reponame" {
  description = "Nombre del repositorio a crear. Este es un nombre lógico usado internamente por Terraform."
  type        = string # Ejemplo: { "agent" = "ai-agent-repo", "api" = "api-repo" }
  default     = "repo-dataia"
}

variable "cloud_run_service_name" {
  description = "Nombre del servicio de Cloud Run."
  type        = string 
}

variable "image_name" {
  description = "Nombre de la imagen del contenedor a desplegar en Cloud Run."
  type        = string 
}