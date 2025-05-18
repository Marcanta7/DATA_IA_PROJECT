locals {
  # Genera nombres de SA completos a partir de los sufijos
  service_accounts_to_create = {
    for service_key, suffix in var.cloud_run_service_account_suffixes :
    service_key => suffix if suffix != null # Solo crea si el sufijo no es nulo (para el frontend opcional)
  }
}

resource "google_service_account" "cloud_run_sas" {
  for_each     = local.service_accounts_to_create
  project      = var.project_id
  account_id   = "${var.app_prefix}-${each.value}" # ej: ai-diet-dev-agent-sa
  display_name = "Service Account for ${var.app_prefix} ${each.key} service"
}

# Permisos comunes para las Service Accounts de Cloud Run
# (BigQuery User, Firestore/Datastore User, GCS Object Viewer)
resource "google_project_iam_member" "cloud_run_sa_bigquery_user" {
  for_each = google_service_account.cloud_run_sas
  project  = var.project_id
  role     = "roles/bigquery.user" # Leer datos, ejecutar queries
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "cloud_run_sa_bigquery_data_editor" {
  for_each = google_service_account.cloud_run_sas
  project  = var.project_id
  role     = "roles/bigquery.dataEditor" # Leer/escribir datos
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "cloud_run_sa_firestore_user" {
  for_each = google_service_account.cloud_run_sas
  project  = var.project_id
  role     = "roles/datastore.user" # Firestore usa roles de Datastore
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "cloud_run_sa_gcs_reader" {
  for_each = google_service_account.cloud_run_sas
  project  = var.project_id
  role     = "roles/storage.objectViewer" # Para leer de GCS (ej: archivos de configuración)
  member   = "serviceAccount:${each.value.email}"
}

# Permiso para invocar otros servicios Cloud Run (si la API llama al Agente, o viceversa)
resource "google_project_iam_member" "cloud_run_sa_run_invoker" {
  for_each = google_service_account.cloud_run_sas
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "serviceAccount:${each.value.email}"
}

# Si usas Secret Manager y Cloud Run necesita acceder a secretos
resource "google_project_iam_member" "cloud_run_sa_secret_accessor" {
  for_each = google_service_account.cloud_run_sas
  project  = var.project_id
  role     = "roles/secretmanager.secretAccessor"
  member   = "serviceAccount:${each.value.email}"
}


# Service Account para Cloud Build (si lo usas para CI/CD de imágenes)
resource "google_service_account" "cloud_build_sa" {
  project      = var.project_id
  account_id   = "${var.app_prefix}-cb-sa"
  display_name = "Service Account for ${var.app_prefix} Cloud Build"
}

# Permisos para Cloud Build SA
resource "google_project_iam_member" "cloud_build_artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer" # Para subir imágenes
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_run_admin" {
  project = var.project_id
  role    = "roles/run.admin" # Para desplegar en Cloud Run
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}

resource "google_project_iam_member" "cloud_build_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser" # Para actuar en nombre de otras SA (ej: la SA de Cloud Run al desplegar)
  member  = "serviceAccount:${google_service_account.cloud_build_sa.email}"
}