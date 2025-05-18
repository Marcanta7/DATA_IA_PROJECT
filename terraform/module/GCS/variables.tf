variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "bucket_name" {
  description = "Nombre para el bucket GCS. Debe ser globalmente único."
  type        = string
}

variable "location" {
  description = "Ubicación para el bucket GCS (ej: US, EU, ASIA, o una región como US-CENTRAL1)."
  type        = string
  default     = "EU" # Ubicación multiregional por defecto
}

variable "storage_class" {
  description = "Clase de almacenamiento para el bucket GCS."
  type        = string
  default     = "STANDARD"
}

variable "force_destroy" {
  description = "Si es true, eliminará todos los objetos del bucket al destruirlo. ¡USAR CON PRECAUCIÓN!"
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Habilitar el versionado de objetos en el bucket."
  type        = bool
  default     = true
}

variable "initial_data_files" {
  description = "Mapa de archivos locales a subir a GCS. La clave es la ruta en GCS, el valor es la ruta local."
  type        = map(string)
  default     = {}
}

variable "public_access_for_frontend" {
  description = "Si es true, configura el bucket para acceso público (para servir un frontend estático)."
  type        = bool
  default     = false
}