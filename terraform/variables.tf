variable "project_id" {
  description = "El ID del proyecto de GCP donde se desplegarán los recursos."
  type        = string
}

variable "region" {
  description = "La región de GCP para el despliegue de recursos."
  type        = string
  default     = "europe-west1"
}

variable "gcp_zone" {
  description = "La zona de GCP para el despliegue de recursos (si aplica)."
  type        = string
  default     = "europe-west1-b"
}

variable "app_name" {
  description = "Un prefijo para los nombres de los recursos, ayuda a identificarlos."
  type        = string
  default     = "ai-diet"
}

variable "app_prefix" {
  description = "Prefijo de la aplicación para nombrar recursos."
  type        = string
}

variable "environment" {
  description = "Entorno de despliegue (ej: dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "firestore_location_id" {
  description = "Ubicación para Firestore (ej: eur3, nam5 o región específica)."
  type        = string
  default     = "eur3"
}

variable "firestore_database_type" {
  description = "Tipo de base de datos Firestore: 'FIRESTORE_NATIVE' o 'DATASTORE_MODE'."
  type        = string
  default     = "FIRESTORE_NATIVE"
}

variable "bigquery_dataset_id_suffix" {
  description = "Sufijo para el ID del dataset de BigQuery (prefijado con app_name y environment)."
  type        = string
  default     = "food_data"
}

variable "dataset_id" {
  description = "ID para el dataset de BigQuery."
  type        = string
  default     = "food_data"
}

variable "bigquery_location" {
  description = "Ubicación para el dataset de BigQuery."
  type        = string
  default     = "EU"
}

variable "table_id" {
  description = "ID de la tabla a crear."
  type        = string
  default     = "mercadona_enriched_clean"
}

variable "bigquery_tables" {
  description = "Lista de tablas a crear en BigQuery, con su schema."
  type = list(object({
    table_id    = string
    schema_path = string
    description = optional(string, "")
  }))
  default = [
    {
      table_id    = "food_products"
      schema_path = "terraform/module/bigquery/schema.json"
      description = "Tabla para almacenar información de productos alimenticios."
    }
  ]
}

variable "gcs_bucket_name_suffix" {
  description = "Sufijo para el nombre del bucket de GCS (prefijado con app_name y environment)."
  type        = string
  default     = "data-artifacts"
}

variable "bucket_name" {
  description = "Nombre completo para el bucket GCS. Debe ser globalmente único."
  type        = string
}

variable "location" {
  description = "Ubicación para el bucket GCS (ej: US, EU, ASIA)."
  type        = string
  default     = "EU"
}

variable "storage_class" {
  description = "Clase de almacenamiento para el bucket GCS."
  type        = string
  default     = "STANDARD"
}

variable "enable_force_destroy_gcs_bucket" {
  description = "Permitir destrucción forzada del bucket GCS (¡cuidado en producción!)."
  type        = bool
  default     = false
}

variable "force_destroy" {
  description = "Eliminar todos los objetos del bucket al destruirlo. ¡USAR CON PRECAUCIÓN!"
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Habilitar versionado de objetos en el bucket."
  type        = bool
  default     = true
}

variable "initial_gcs_data_files" {
  description = "Mapa de archivos locales a subir a GCS. Clave = ruta en GCS, valor = ruta local."
  type        = map(string)
  default = {
    "data/mercadona_products.csv"    = "terraform/module/GCS/mercadona_products.csv"
    "data/openfoodfacts_export.csv"  = "terraform/module/GCS/openfoodfacts_export.csv"
    "data/precios.csv"               = "nodes/precios.csv"
  }
}

variable "initial_data_files" {
  description = "Mapa de archivos iniciales para otros buckets (si aplica)."
  type        = map(string)
  default     = {}
}

variable "public_access_for_frontend" {
  description = "Permitir acceso público al bucket (para servir un frontend estático)."
  type        = bool
  default     = false
}

variable "artifact_registry_repositories" {
  description = "Mapa de repositorios de Artifact Registry. Clave = nombre lógico."
  type        = map(string)
  default = {
    "agent"    = "ai-agent-repo"
    "api"      = "api-repo"
    "frontend" = "frontend-repo"
  }
}

variable "repositories" {
  description = "Mapa de repositorios adicionales a crear."
  type        = map(string)
}

variable "reponame" {
  description = "Nombre lógico para un repositorio específico."
  type        = string
  default     = "repo-dataia"
}

variable "cloud_run_agent_settings" {
  description = "Configuración del servicio Cloud Run del Agente IA."
  type = object({
    image_name                  = string
    container_port              = number
    memory                      = string
    cpu                         = string
    min_instances               = number
    max_instances               = number
    allow_unauthenticated       = bool
    service_account_name_suffix = string
  })
  default = {
    image_name                  = "diet-agent-service"
    container_port              = 8080
    memory                      = "512Mi"
    cpu                         = "1"
    min_instances               = 0
    max_instances               = 2
    allow_unauthenticated       = false
    service_account_name_suffix = "agent-sa"
  }
}

variable "cloud_run_api_settings" {
  description = "Configuración del servicio Cloud Run de la API."
  type = object({
    image_name                  = string
    container_port              = number
    memory                      = string
    cpu                         = string
    min_instances               = number
    max_instances               = number
    allow_unauthenticated       = bool
    service_account_name_suffix = string
  })
  default = {
    image_name                  = "diet-api-service"
    container_port              = 8000
    memory                      = "512Mi"
    cpu                         = "1"
    min_instances               = 0
    max_instances               = 3
    allow_unauthenticated       = true
    service_account_name_suffix = "api-sa"
  }
}

variable "cloud_run_frontend_settings" {
  description = "Configuración del servicio Cloud Run del Frontend."
  type = object({
    enabled                    = bool
    image_name                 = string
    container_port             = number
    memory                     = string
    cpu                        = string
    min_instances              = number
    max_instances              = number
    allow_unauthenticated      = bool
    service_account_name_suffix = string
  })
  default = {
    enabled                    = true
    image_name                 = "diet-frontend-service"
    container_port             = 3000
    memory                     = "256Mi"
    cpu                        = "1"
    min_instances              = 0
    max_instances              = 2
    allow_unauthenticated      = true
    service_account_name_suffix = "frontend-sa"
  }
}

variable "cloud_run_service_name" {
  description = "Nombre del servicio de Cloud Run (generador de tabla, por ejemplo)."
  type        = string
  default     = "table-bq-generator"
}

variable "image_name" {
  description = "Nombre de la imagen del contenedor (generador de tabla, por ejemplo)."
  type        = string
  default     = "image-bq-generator"
}

variable "cloud_run_service_account_suffixes" {
  description = "Mapa de sufijos de Service Accounts para servicios Cloud Run."
  type        = map(string)
}

variable "service_name" {
  description = "Nombre para un servicio específico de Cloud Run."
  type        = string
}

variable "container_image" {
  description = "URL completa de la imagen del contenedor (Artifact Registry)."
  type        = string
}

variable "container_port" {
  description = "Puerto en el que escucha el contenedor."
  type        = number
  default     = 8080
}

variable "service_account_email" {
  description = "Email de la Service Account para el servicio Cloud Run."
  type        = string
}

variable "allow_unauthenticated" {
  description = "Permitir invocaciones no autenticadas al servicio Cloud Run."
  type        = bool
  default     = false
}

variable "memory" {
  description = "Límite de memoria para el contenedor."
  type        = string
  default     = "512Mi"
}

variable "cpu" {
  description = "Límite de CPU para el contenedor."
  type        = string
  default     = "1"
}

variable "min_instances" {
  description = "Número mínimo de instancias del contenedor."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Número máximo de instancias del contenedor."
  type        = number
  default     = 10
}

variable "container_concurrency" {
  description = "Número máximo de solicitudes concurrentes por instancia."
  type        = number
  default     = 80
}

variable "enable_vpc_connector" {
  description = "Habilita la creación de un conector Serverless VPC Access."
  type        = bool
  default     = false
}

variable "vpc_connector_ip_cidr_range" {
  description = "Rango CIDR /28 para el conector VPC. Requerido si enable_vpc_connector es true."
  type        = string
  default     = "10.8.0.0/28"
}

variable "network_name" {
  description = "Nombre de la red VPC a la que se conectará. Por defecto 'default'."
  type        = string
  default     = "default"
}

variable "ip_cidr_range" {
  description = "Rango IP CIDR /28 para el conector VPC."
  type        = string
}

variable "min_throughput" {
  description = "Rendimiento mínimo del conector en Mbps."
  type        = number
  default     = 200
}

variable "max_throughput" {
  description = "Rendimiento máximo del conector en Mbps."
  type        = number
  default     = 300
}