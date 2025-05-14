resource "google_project_service" "firestore" {
  service = "firestore.googleapis.com"
}

resource "google_firestore_database" "default" {
  name        = "(default)"
  project     = var.gcp_project_id
  location_id = var.gcp_region
  type        = "NATIVE"
  depends_on  = [google_project_service.firestore]
}