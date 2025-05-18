output "bucket_name_output" {
  description = "El nombre del bucket GCS."
  value       = google_storage_bucket.bucket.name
}

output "bucket_url_output" {
  description = "La URL gs:// del bucket GCS."
  value       = "gs://${google_storage_bucket.bucket.name}"
}

output "bucket_self_link_output" {
  description = "El self_link del bucket GCS."
  value       = google_storage_bucket.bucket.self_link
}

output "uploaded_files_gcs_paths" {
  description = "Rutas GCS de los archivos subidos."
  value       = { for k, v in google_storage_bucket_object.data_files : k => "gs://${v.bucket}/${v.name}" }
}