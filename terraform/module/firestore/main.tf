
resource "google_app_engine_application" "app" {
  project       = var.project_id
  location_id   = var.location_id 
  database_type = var.database_type

  depends_on = [var.app_engine_api_dependency]
}


resource "google_firestore_database" "database" {
  provider    = google-beta 
  name        = "(default)" 
  location_id = google_app_engine_application.app.location_id 
  type        = var.database_type

  depends_on = [google_app_engine_application.app]
}
