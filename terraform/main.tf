locals {
  project_id = var.gcp_project_id
  region     = var.gcp_region
  app_prefix = "${var.app_name}-${var.environment}"

  # Nombre completo del bucket GCS
  gcs_bucket_name = "${local.app_prefix}-${var.gcs_bucket_name_suffix}"

  # Nombre completo del dataset de BigQuery
  bigquery_dataset_id = "${replace(var.app_name, "-", "_")}_${var.environment}_${var.bigquery_dataset_id_suffix}"

  # URLs de los repositorios de Artifact Registry
  artifact_registry_repo_urls = {
    for key, name_suffix in var.artifact_registry_repositories :
    key => "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${local.app_prefix}-${name_suffix}/${key}-image" # Asumimos que la imagen se llamará como la clave + '-image'
  }
}

# Habilitación de APIs necesarias para el proyecto
resource "google_project_service" "gcp_services" {
  project = local.project_id
  for_each = toset([
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "bigquery.googleapis.com",
    "firestore.googleapis.com",
    "storage-api.googleapis.com", # storage.googleapis.com es el endpoint, la API es esta
    "cloudbuild.googleapis.com",    # Para construir imágenes si usas Cloud Build
    "compute.googleapis.com",       # Dependencia para VPC Access, etc.
    "vpcaccess.googleapis.com",     # Para Serverless VPC Access
    "appengine.googleapis.com",     # Necesario para Firestore para configurar la ubicación
  ])
  service                    = each.key
  disable_dependent_services = false # No deshabilitar servicios que dependen de estos
  disable_on_destroy         = false # Generalmente no se quieren deshabilitar al destruir
}

module "iam" {
  source     = "./module/iam"
  project_id = local.project_id
  app_prefix = local.app_prefix
  region     = local.region

  cloud_run_service_account_suffixes = {
    agent    = var.cloud_run_agent_settings.service_account_name_suffix
    api      = var.cloud_run_api_settings.service_account_name_suffix
    frontend = var.cloud_run_frontend_settings.enabled ? var.cloud_run_frontend_settings.service_account_name_suffix : null
  }
  depends_on = [google_project_service.gcp_services]
}

module "gcs" {
  source                 = "./module/gcs"
  project_id             = local.project_id
  bucket_name            = local.gcs_bucket_name
  location               = var.gcp_region # Los buckets son multiregionales por defecto (ej: EU, US) o regionales
  force_destroy          = var.enable_force_destroy_gcs_bucket && var.environment != "prod"
  initial_data_files     = var.initial_gcs_data_files
  public_access_for_frontend = var.cloud_run_frontend_settings.enabled ? false : true # Hacer público si el frontend se sirve desde GCS
  depends_on             = [google_project_service.gcp_services]
}

module "artifact_registry" {
  source       = "./module/artifact_registry"
  project_id   = local.project_id
  region       = local.region
  app_prefix   = local.app_prefix
  repositories = var.artifact_registry_repositories # Pasa el mapa directamente
  depends_on   = [google_project_service.gcp_services]
}

module "bigquery" {
  source           = "./module/bigquery"
  project_id       = local.project_id
  dataset_id       = local.bigquery_dataset_id
  dataset_location = var.bigquery_location
  tables           = var.bigquery_tables
  depends_on       = [google_project_service.gcp_services]
}

module "firestore" {
  source          = "./module/firestore"
  project_id      = local.project_id
  location_id     = var.firestore_location_id
  database_type   = var.firestore_database_type
  app_engine_api_dependency = google_project_service.gcp_services["appengine.googleapis.com"]
  depends_on      = [google_project_service.gcp_services]
}

module "network" {
  count         = var.enable_vpc_connector ? 1 : 0
  source        = "./module/network"
  project_id    = local.project_id
  region        = local.region
  app_prefix    = local.app_prefix
  ip_cidr_range = var.vpc_connector_ip_cidr_range
  depends_on    = [google_project_service.gcp_services["vpcaccess.googleapis.com"]]
}

# --- Servicios Cloud Run ---
# Asume que las imágenes Docker ya existen en Artifact Registry.
# Considera usar Cloud Build para automatizar la creación y subida de imágenes.

module "cloud_run_agent" {
  source              = "./module/cloud_run"
  project_id          = local.project_id
  region              = local.region
  service_name        = "${local.app_prefix}-agent-service"
  # La URL completa de la imagen se construye así: <region>-docker.pkg.dev/<project_id>/<repo_id>/<image_name>:<tag>
  container_image     = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${module.artifact_registry.repository_ids["agent"]}/${var.cloud_run_agent_settings.image_name}:latest" # Ajusta el tag según necesites
  container_port      = var.cloud_run_agent_settings.container_port
  service_account_email = module.iam.service_account_emails["agent"]
  allow_unauthenticated = var.cloud_run_agent_settings.allow_unauthenticated
  memory              = var.cloud_run_agent_settings.memory
  cpu                 = var.cloud_run_agent_settings.cpu
  min_instances       = var.cloud_run_agent_settings.min_instances
  max_instances       = var.cloud_run_agent_settings.max_instances
  vpc_connector_id    = var.enable_vpc_connector ? module.network[0].connector_id : null
  env_vars = [
    { name = "GCP_PROJECT_ID", value = local.project_id },
    { name = "BIGQUERY_DATASET_ID", value = module.bigquery.dataset_id_output }, # Usar la salida del módulo
    { name = "FIRESTORE_PROJECT_ID", value = local.project_id }, # Firestore usa el ID del proyecto
    # Añade aquí otras variables de entorno que necesite tu agente
    # Ejemplo: { name = "OPENAI_API_KEY_SECRET", secret_name = "projects/your-project-id/secrets/openai-api-key/versions/latest" }
  ]
  # secrets = [ # Ejemplo de cómo montar un secreto de Secret Manager
  #   { name = "API_KEY", secret_name = "mi-secreto-api-key", secret_version = "latest" }
  # ]
  depends_on = [module.artifact_registry, module.iam, module.bigquery, module.firestore]
}

module "cloud_run_api" {
  source              = "./module/cloud_run"
  project_id          = local.project_id
  region              = local.region
  service_name        = "${local.app_prefix}-api-service"
  container_image     = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${module.artifact_registry.repository_ids["api"]}/${var.cloud_run_api_settings.image_name}:latest"
  container_port      = var.cloud_run_api_settings.container_port
  service_account_email = module.iam.service_account_emails["api"]
  allow_unauthenticated = var.cloud_run_api_settings.allow_unauthenticated
  memory              = var.cloud_run_api_settings.memory
  cpu                 = var.cloud_run_api_settings.cpu
  min_instances       = var.cloud_run_api_settings.min_instances
  max_instances       = var.cloud_run_api_settings.max_instances
  vpc_connector_id    = var.enable_vpc_connector ? module.network[0].connector_id : null
  env_vars = [
    { name = "GCP_PROJECT_ID", value = local.project_id },
    { name = "BIGQUERY_DATASET_ID", value = module.bigquery.dataset_id_output },
    { name = "FIRESTORE_PROJECT_ID", value = local.project_id },
    { name = "AI_AGENT_URL", value = module.cloud_run_agent.service_url }, # Para que la API pueda llamar al agente
    # Añade aquí otras variables de entorno que necesite tu API
  ]
  depends_on = [module.artifact_registry, module.iam, module.cloud_run_agent] # Depende del agente si necesita su URL
}

module "cloud_run_frontend" {
  count               = var.cloud_run_frontend_settings.enabled ? 1 : 0
  source              = "./module/cloud_run"
  project_id          = local.project_id
  region              = local.region
  service_name        = "${local.app_prefix}-frontend-service"
  container_image     = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${module.artifact_registry.repository_ids["frontend"]}/${var.cloud_run_frontend_settings.image_name}:latest"
  container_port      = var.cloud_run_frontend_settings.container_port
  service_account_email = module.iam.service_account_emails["frontend"]
  allow_unauthenticated = var.cloud_run_frontend_settings.allow_unauthenticated
  memory              = var.cloud_run_frontend_settings.memory
  cpu                 = var.cloud_run_frontend_settings.cpu
  min_instances       = var.cloud_run_frontend_settings.min_instances
  max_instances       = var.cloud_run_frontend_settings.max_instances
  vpc_connector_id    = var.enable_vpc_connector ? module.network[0].connector_id : null
  env_vars = [
    { name = "API_BASE_URL", value = module.cloud_run_api.service_url }, # Para que el frontend sepa dónde está la API
    # Añade aquí otras variables de entorno que necesite tu frontend
  ]
  depends_on = [module.artifact_registry, module.iam, module.cloud_run_api] # Depende de la API si necesita su URL
}

# EXTRAS: Cloud Run Job para ingesta de datos (ejemplo)
# Necesitarás una imagen Docker específica para este job que lea de GCS y escriba en BigQuery.
/*
module "cloud_run_data_ingestion_job" {
  source                  = "./modules/cloud_run_job" # Asume que creas este módulo
  project_id              = local.project_id
  region                  = local.region
  job_name                = "${local.app_prefix}-data-ingest-job"
  container_image         = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${module.artifact_registry.repository_ids["agent"]}/data-ingestion-tool:latest" # Usa una imagen dedicada
  service_account_email   = module.iam.service_account_emails["agent"] # Reutiliza SA o crea una específica
  memory_limit            = "1Gi"
  cpu_limit               = "1"
  task_timeout_seconds    = 1800 # 30 minutos
  env_vars = [
    { name = "GCP_PROJECT_ID", value = local.project_id },
    { name = "BIGQUERY_DATASET_ID", value = module.bigquery.dataset_id_output },
    { name = "GCS_BUCKET_NAME", value = module.gcs.bucket_name_output },
    { name = "GCS_MERCADONA_FILE_PATH", value = "data/mercadona_products.csv" },
    # ... otras variables para tu script de ingesta
  ]
  depends_on = [
    module.artifact_registry,
    module.iam,
    module.gcs,
    module.bigquery
  ]
}
*/