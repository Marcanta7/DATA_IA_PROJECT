variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "region" {
  description = "Región GCP para el Cloud Run Job."
  type        = string
}

variable "job_name" {
  description = "Nombre para el Cloud Run Job."
  type        = string
}

variable "container_image" {
  description = "URL completa de la imagen del contenedor en Artifact Registry."
  type        = string
}

variable "service_account_email" {
  description = "Email de la Service Account con la que se ejecutará el job."
  type        = string
}

variable "memory_limit" {
  description = "Límite de memoria para el contenedor (ej: '512Mi', '1Gi')."
  type        = string
  default     = "512Mi"
}

variable "cpu_limit" {
  description = "Límite de CPU para el contenedor (ej: '1', '2')."
  type        = string
  default     = "1"
}

variable "task_timeout_seconds" {
  description = "Tiempo de espera para cada tarea en el job, en segundos."
  type        = number
  default     = 600 # 10 minutos
}

variable "max_retries" {
  description = "Número de reintentos para una tarea fallida."
  type        = number
  default     = 3
}

variable "env_vars" {
  description = "Lista de variables de entorno para el contenedor del job."
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "secrets" {
  description = "Lista de secretos de Secret Manager para montar como variables de entorno para el job."
  type = list(object({
    name           = string
    secret_name    = string
    secret_version = string
  }))
  default = []
}

variable "vpc_connector_id" {
  description = "ID del Serverless VPC Access Connector a usar."
  type        = string
  default     = null
}

variable "vpc_egress" {
  description = "Configuración de salida VPC para el job."
  type        = string
  default     = null
}