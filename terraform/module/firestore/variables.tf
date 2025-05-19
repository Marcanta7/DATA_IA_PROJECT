variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "location_id" {
  description = "Ubicación de la base de datos Firestore. Usa 'nam5' (Norteamérica) o 'eur3' (Europa) para multiregión, o una región específica (ej: 'us-central1')."
  type        = string
  default     = "eur3"
}

variable "database_type" {
  description = "Tipo de base de datos Firestore: 'FIRESTORE_NATIVE' o 'DATASTORE_MODE'."
  type        = string
  default     = "FIRESTORE_NATIVE"
  validation {
    condition     = contains(["FIRESTORE_NATIVE", "DATASTORE_MODE"], var.database_type)
    error_message = "El tipo de base de datos debe ser 'FIRESTORE_NATIVE' o 'DATASTORE_MODE'."
  }
}

variable "app_engine_api_dependency" {
  description = "Dependencia explícita del recurso google_project_service para la API de App Engine."
  type        = any # Se pasa el recurso directamente
}