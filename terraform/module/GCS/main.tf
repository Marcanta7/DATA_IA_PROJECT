resource "google_storage_bucket" "bucket" {
  project                     = var.project_id
  name                        = var.bucket_name
  location                    = var.location
  storage_class               = var.storage_class
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true # Recomendado para nuevos buckets

  versioning {
    enabled = var.versioning_enabled
  }

  # Política de ciclo de vida: ejemplo para eliminar versiones antiguas
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 3 # Mantiene las 3 versiones más recientes no actuales
      # O puedes usar days_since_noncurrent_time = 7
    }
  }
  # Si el frontend se sirve desde GCS, configura la página de índice y error
  dynamic "website" {
    for_each = var.public_access_for_frontend ? [1] : []
    content {
      main_page_suffix = "index.html"
      not_found_page   = "404.html"
    }
  }
}

# IAM para acceso público si es para un frontend estático
resource "google_storage_bucket_iam_member" "public_viewer" {
  count  = var.public_access_for_frontend ? 1 : 0
  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Subir archivos iniciales
resource "google_storage_bucket_object" "data_files" {
  for_each     = var.initial_data_files
  bucket       = google_storage_bucket.bucket.name
  name         = each.key # Ruta del objeto en GCS
  source       = each.value   # Ruta al archivo local
  content_type = substr(each.key, length(each.key) - 3, -1) == "csv" ? "text/csv" : (substr(each.key, length(each.key) - 4, -1) == "json" ? "application/json" : "application/octet-stream")

  depends_on = [google_storage_bucket.bucket]
}