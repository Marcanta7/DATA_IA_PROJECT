output "service_name" {
  description = "El nombre del servicio Cloud Run."
  value       = google_cloud_run_v2_service.service.name
}

output "service_url" {
  description = "La URL del servicio Cloud Run."
  value       = google_cloud_run_v2_service.service.uri
}

output "service_latest_revision" {
  description = "Nombre de la última revisión creada del servicio Cloud Run."
  value       = google_cloud_run_v2_service.service.latest_ready_revision
}