variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "region" {
  description = "Región GCP para los repositorios de Artifact Registry."
  type        = string
}

variable "app_prefix" {
  description = "Prefijo de la aplicación para nombrar los repositorios."
  type        = string
}

variable "repositories" {
  description = "Mapa de repositorios a crear. La clave es un nombre lógico (usado internamente por Terraform), el valor es el sufijo del nombre del repositorio."
  type        = map(string) # Ejemplo: { "agent" = "ai-agent-repo", "api" = "api-repo" }
}