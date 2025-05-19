variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "region" {
  description = "Región GCP para el servicio Cloud Run."
  type        = string
}

variable "service_name" {
  description = "Nombre para el servicio Cloud Run."
  type        = string
}

variable "container_image" {
  description = "URL completa de la imagen del contenedor en Artifact Registry (ej: <region>-docker.pkg.dev/<project>/<repo>/<image>:<tag>)."
  type        = string
}

variable "container_port" {
  description = "Puerto en el que escucha el contenedor."
  type        = number
  default     = 8080
}

variable "service_account_email" {
  description = "Email de la Service Account con la que se ejecutará el servicio."
  type        = string
}

variable "allow_unauthenticated" {
  description = "Permitir invocaciones no autenticadas al servicio."
  type        = bool
  default     = false
}

variable "memory" {
  description = "Límite de memoria para el contenedor (ej: '512Mi', '1Gi')."
  type        = string
  default     = "512Mi"
}

variable "cpu" {
  description = "Límite de CPU para el contenedor (ej: '1', '2', '0.5' para CPU bajo demanda; o '1000m' para CPU siempre asignada). "
  type        = string
  default     = "1" # 1 vCPU, bajo demanda
}

variable "min_instances" {
  description = "Número mínimo de instancias del contenedor. Poner a 0 para escalar a cero."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Número máximo de instancias del contenedor."
  type        = number
  default     = 10 # Ajustar según sea necesario
}

variable "container_concurrency" {
  description = "Número máximo de solicitudes concurrentes que pueden enviarse a una instancia del contenedor."
  type        = number
  default     = 80
}

variable "timeout_seconds" {
  description = "Tiempo de espera de la solicitud para el servicio en segundos."
  type        = number
  default     = 300 # 5 minutos
}

variable "env_vars" {
  description = "Lista de variables de entorno para el contenedor. Cada item es un objeto con 'name' y 'value'."
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "secrets" {
  description = "Lista de secretos de Secret Manager para montar como variables de entorno. Cada item tiene 'name' (nombre de la var env), 'secret_name' (ID del secreto en Secret Manager), y 'secret_version' (ej: 'latest')."
  type = list(object({
    name           = string # Nombre de la variable de entorno
    secret_name    = string # Nombre del secreto en Secret Manager (sin 'projects/.../secrets/')
    secret_version = string # ej: "latest" o un número de versión
  }))
  default = []
}

variable "vpc_connector_id" {
  description = "ID del Serverless VPC Access Connector a usar. Ej: projects/PROJECT_ID/locations/REGION/connectors/CONNECTOR_NAME"
  type        = string
  default     = null
}

variable "vpc_egress" {
  description = "Configuración de salida VPC. 'all-traffic' o 'private-ranges-only'."
  type        = string
  default     = null # Por defecto no hay salida VPC a menos que se especifique el conector
  validation {
    condition     = var.vpc_egress == null || contains(["all-traffic", "private-ranges-only"], var.vpc_egress)
    error_message = "La salida VPC debe ser 'all-traffic' o 'private-ranges-only' si se especifica."
  }
}