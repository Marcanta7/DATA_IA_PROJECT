resource "google_bigquery_dataset" "dataset" {
  project                    = var.project_id
  dataset_id                 = var.dataset_id
  friendly_name              = var.dataset_description
  description                = var.dataset_description
  location                   = var.dataset_location
  delete_contents_on_destroy = var.delete_contents_on_destroy

}

resource "google_bigquery_table" "tables" {
  for_each    = { for tbl in var.tables : tbl.table_id => tbl if fileexists(tbl.schema_path) } # Solo crea si el archivo de schema existe
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.dataset.dataset_id
  table_id    = each.value.table_id
  description = each.value.description != "" ? each.value.description : "Tabla ${each.value.table_id}"

  schema = file(each.value.schema_path)
  deletion_protection = false 

  depends_on = [google_bigquery_dataset.dataset]
}

# Define structure for clean enriched table
resource "google_bigquery_table" "clean_enriched_table" {
  dataset_id = google_bigquery_dataset.food_data.dataset_id
  table_id   = var.table_id
  project    = var.project_id
  
  deletion_protection = false

  # Use the same schema as the original table
  schema = file("${path.module}/schema.json")
}
