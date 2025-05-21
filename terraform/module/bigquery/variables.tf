variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "dataset_id" {
  description = "ID para el dataset de BigQuery."
  type        = string
}

variable "dataset_location" {
  description = "Ubicación para el dataset de BigQuery (ej: US, EU, asia-northeast1)."
  type        = string
  default     = "EU"
}

variable "dataset_description" {
  description = "Descripción para el dataset de BigQuery."
  type        = string
  default     = "Dataset para la aplicación de dietas con IA"
}

variable "delete_contents_on_destroy" {
  description = "Si es true, elimina todas las tablas del dataset al destruirlo. ¡USAR CON PRECAUCIÓN!"
  type        = bool
  default     = false # Cambiar a true solo para dev/test
}

variable "tables" {
  description = "Lista de tablas a crear. Cada objeto debe tener 'table_id' y 'schema_path' (ruta al archivo JSON del schema)."
  type = list(object({
    table_id    = string
    schema_path = string
    description = optional(string, "")
  }))
  default = []
}

variable "table_id" {
  description = "ID de la tabla a crear."
  type        = string
}