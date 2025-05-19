output "connector_id" {
  description = "ID del Conector VPC Access."
  value       = google_vpc_access_connector.connector.id
}

output "connector_name" {
  description = "Nombre del Conector VPC Access."
  value       = google_vpc_access_connector.connector.name
}

output "connector_self_link" {
  description = "Self-link del Conector VPC Access."
  value       = google_vpc_access_connector.connector.self_link
}