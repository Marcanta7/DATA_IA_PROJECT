resource "google_bigquery_dataset" "food_data" {
  dataset_id                  = var.dataset_id
  project                     = var.project_id
  location                    = var.location
  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "products" {
  dataset_id = google_bigquery_dataset.food_data.dataset_id
  table_id   = var.table_id
  project    = var.project_id

  schema = file("${path.module}/schema.json")

  time_partitioning {
    type = "DAY"
  }
}