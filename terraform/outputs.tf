output "gcs_bucket_name" {
  description = "Nombre del bucket de GCS para datos y artefactos."
  value       = module.gcs.bucket_name_output
}

output "gcs_bucket_url" {
  description = "URL del bucket de GCS (gs://)."
  value       = module.gcs.bucket_url_output
}

output "artifact_registry_repository_urls" {
  description = "URLs de los repositorios de Artifact Registry creados."
  value       = { for k, repo in module.artifact_registry.repositories_details : k => repo.url }
}

output "bigquery_dataset_full_id" {
  description = "ID completo del dataset de BigQuery (project:dataset)."
  value       = module.bigquery.dataset_full_id_output
}

output "firestore_database_name" {
  description = "Nombre de la base de datos Firestore."
  value       = module.firestore.database_name_output
}

output "cloud_run_agent_service_url" {
  description = "URL del servicio Cloud Run del Agente IA."
  value       = module.cloud_run_agent.service_url
}

output "cloud_run_api_service_url" {
  description = "URL del servicio Cloud Run de la API."
  value       = module.cloud_run_api.service_url
}

output "cloud_run_frontend_service_url" {
  description = "URL del servicio Cloud Run del Frontend (si está habilitado)."
  value       = var.cloud_run_frontend_settings.enabled ? module.cloud_run_frontend[0].service_url : "Frontend no desplegado vía Cloud Run."
}

output "cloud_run_service_account_emails" {
  description = "Emails de las Service Accounts creadas para Cloud Run."
  value       = module.iam.service_account_emails
}

output "vpc_access_connector_id" {
  description = "ID del Serverless VPC Access Connector (si está habilitado)."
  value       = var.enable_vpc_connector ? module.network[0].connector_id : "VPC Connector no habilitado."
}