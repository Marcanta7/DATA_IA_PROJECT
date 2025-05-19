variable "gcp_project_id" {
  description = "El ID del proyecto de GCP donde se desplegarán los recursos."
  type        = string
}

variable "gcp_region" {
  description = "La región de GCP para el despliegue de recursos."
  type        = string
  default     = "europe-west1" # Ejemplo, ajústalo a tu región preferida
}

variable "gcp_zone" {
  description = "La zona de GCP para el despliegue de recursos (si aplica)."
  type        = string
  default     = "europe-west1-b" # Ejemplo, ajústalo
}

variable "app_name" {
  description = "Un prefijo para los nombres de los recursos, ayuda a identificarlos."
  type        = string
  default     = "ai-diet"
}

variable "environment" {
  description = "Entorno de despliegue (ej: dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "firestore_location_id" {
  description = "Ubicación para la base de datos Firestore. Usa 'nam5' (Norteamérica) o 'eur3' (Europa) para multiregión, o una región específica."
  type        = string
  default     = "eur3" # O tu multiregión preferida como nam5, o una región específica
}

variable "firestore_database_type" {
  description = "Tipo de base de datos Firestore: 'FIRESTORE_NATIVE' o 'DATASTORE_MODE'."
  type        = string
  default     = "FIRESTORE_NATIVE"
}

variable "bigquery_dataset_id_suffix" {
  description = "Sufijo para el ID del dataset de BigQuery (se prefijará con app_name y environment)."
  type        = string
  default     = "food_data"
}

variable "bigquery_location" {
  description = "Ubicación para el dataset de BigQuery."
  type        = string
  default     =  "EU"
}

variable "gcs_bucket_name_suffix" {
  description = "Sufijo para el nombre del bucket de GCS (se prefijará con app_name y environment)."
  type        = string
  default     = "data-artifacts"
}

variable "enable_force_destroy_gcs_bucket" {
  description = "Permitir la destrucción forzada del bucket GCS (¡cuidado en producción!)."
  type        = bool
  default     = false # Cambiar a true solo para entornos de desarrollo/prueba
}


variable "artifact_registry_repositories" {
  description = "Mapa de repositorios de Artifact Registry a crear. La clave es un nombre lógico (ej: 'agent', 'api'), el valor es el nombre del repo."
  type        = map(string)
  default = {
    "agent"    = "ai-agent-repo"
    "api"      = "api-repo"
    "frontend" = "frontend-repo"
  }
}

variable "cloud_run_agent_settings" {
  description = "Configuración para el servicio Cloud Run del Agente IA."
  type = object({
    image_name                = string
    container_port            = number
    memory                    = string
    cpu                       = string
    min_instances             = number
    max_instances             = number
    allow_unauthenticated     = bool
    service_account_name_suffix = string
  })
  default = {
    image_name                = "diet-agent-service" # Solo el nombre de la imagen, el repo se deduce
    container_port            = 8080
    memory                    = "512Mi"
    cpu                       = "1"
    min_instances             = 0
    max_instances             = 2
    allow_unauthenticated     = false # El agente podría ser invocado internamente por la API
    service_account_name_suffix = "agent-sa"
  }
}

variable "cloud_run_api_settings" {
  description = "Configuración para el servicio Cloud Run de la API."
  type = object({
    image_name                = string
    container_port            = number
    memory                    = string
    cpu                       = string
    min_instances             = number
    max_instances             = number
    allow_unauthenticated     = bool
    service_account_name_suffix = string
  })
  default = {
    image_name                = "diet-api-service"
    container_port            = 8000 # FastAPI usa 8000 por defecto
    memory                    = "512Mi"
    cpu                       = "1"
    min_instances             = 0
    max_instances             = 3
    allow_unauthenticated     = true # La API probablemente sea pública
    service_account_name_suffix = "api-sa"
  }
}

variable "cloud_run_frontend_settings" {
  description = "Configuración para el servicio Cloud Run del Frontend (si es una app contenerizada)."
  type = object({
    enabled                   = bool
    image_name                = string
    container_port            = number
    memory                    = string
    cpu                       = string
    min_instances             = number
    max_instances             = number
    allow_unauthenticated     = bool
    service_account_name_suffix = string
  })
  default = {
    enabled                   = true # Cambiar a false si no hay frontend contenerizado
    image_name                = "diet-frontend-service"
    container_port            = 3000 # Puerto común para apps de frontend (Node.js, etc.)
    memory                    = "256Mi"
    cpu                       = "1"
    min_instances             = 0
    max_instances             = 2
    allow_unauthenticated     = true
    service_account_name_suffix = "frontend-sa"
  }
}

variable "bigquery_tables" {
  description = "Lista de tablas a crear en BigQuery, con su schema."
  type = list(object({
    table_id    = string
    schema_path = string # Ruta al archivo JSON del schema
    description = optional(string, "")
  }))
  default = [
    {
      table_id    = "food_products"
      # Asume que tienes un schema.json en la raíz del proyecto o ajusta la ruta
      schema_path = "terraform/module/bigquery/schema.json"
      description = "Tabla para almacenar información de productos alimenticios."
    },
    # Puedes añadir más tablas aquí
    # {
    #   table_id    = "user_diet_preferences"
    #   schema_path = "path/to/your/user_preferences_schema.json"
    #   description = "Preferencias dietéticas de los usuarios."
    # }
  ]
}

# Variables para la carga inicial de datos en GCS
variable "initial_gcs_data_files" {
  description = "Mapa de archivos locales a subir a GCS. La clave es la ruta en GCS, el valor es la ruta local."
  type        = map(string)
  default = {
    "data/mercadona_products.csv"    = "terraform/module/GCS/mercadona_products.csv"
    "data/openfoodfacts_export.csv"  = "terraform/module/GCS/openfoodfacts_export.csv"
    "data/precios.csv"               = "nodes/precios.csv"
    # "other_data/another_file.json" = "path/to/local/another_file.json"
  }
}

variable "enable_vpc_connector" {
  description = "Habilitar la creación de un Serverless VPC Access Connector."
  type        = bool
  default     = false # Habilitar si tus Cloud Run necesitan acceder a recursos en una VPC privada
}

variable "vpc_connector_ip_cidr_range" {
  description = "Rango IP CIDR /28 no utilizado para el conector VPC. Requerido si enable_vpc_connector es true."
  type        = string
  default     = "10.8.0.0/28" # ¡ASEGÚRATE DE QUE ESTE RANGO ESTÉ LIBRE EN TU VPC!
}