output "service_account_emails" {
  description = "Emails de las Service Accounts creadas para Cloud Run."
  value       = { for k, sa in google_service_account.cloud_run_sas : k => sa.email }
}

output "service_account_names" {
  description = "Nombres completos de las Service Accounts creadas para Cloud Run."
  value       = { for k, sa in google_service_account.cloud_run_sas : k => sa.name }
}

output "cloud_build_sa_email" {
  description = "Email de la Service Account para Cloud Build."
  value       = google_service_account.cloud_build_sa.email
}