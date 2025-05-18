output "database_name_output" {
  description = "El nombre de la base de datos Firestore (será '(default)')."
  value       = google_firestore_database.database.name
}

output "database_location_id_output" {
  description = "La ubicación de la base de datos Firestore."
  value       = google_firestore_database.database.location_id
}

output "app_engine_location_id_output" {
  description = "La ubicación ID fijada por la aplicación App Engine, que dicta la región de Firestore."
  value       = google_app_engine_application.app.location_id
}