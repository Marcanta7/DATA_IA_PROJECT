output "dataset_id_output" {
  description = "El ID del dataset de BigQuery."
  value       = google_bigquery_dataset.dataset.dataset_id
}

output "dataset_full_id_output" {
  description = "El ID completo del dataset de BigQuery en formato project:dataset."
  value       = "${var.project_id}:${google_bigquery_dataset.dataset.dataset_id}"
}

output "dataset_self_link_output" {
  description = "El self_link del dataset de BigQuery."
  value       = google_bigquery_dataset.dataset.self_link
}

output "table_ids_output" {
  description = "IDs de las tablas creadas en BigQuery."
  value       = { for id, tbl in google_bigquery_table.tables : id => tbl.table_id }
}