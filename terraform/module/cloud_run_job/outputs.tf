output "job_name_output" {
  description = "El nombre del Cloud Run Job."
  value       = google_cloud_run_v2_job.job.name
}

output "job_uid_output" {
  description = "El UID del Cloud Run Job."
  value       = google_cloud_run_v2_job.job.uid
}

output "job_latest_created_execution_name" {
  description = "Nombre de la última ejecución creada del job (si se ha ejecutado)."
  value       = try(google_cloud_run_v2_job.job.latest_created_execution[0].name, "Job no ejecutado aún")
}