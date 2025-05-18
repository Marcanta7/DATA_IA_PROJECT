variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "app_prefix" {
  description = "Prefijo de la aplicación para nombrar recursos."
  type        = string
}

variable "region" {
  description = "Región GCP."
  type        = string
}

variable "cloud_run_service_account_suffixes" {
  description = "Mapa de sufijos para los nombres de las Service Accounts de Cloud Run (la clave es el nombre lógico del servicio, ej: 'agent', 'api')."
  type        = map(string)
}