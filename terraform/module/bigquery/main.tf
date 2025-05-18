resource "google_bigquery_dataset" "dataset" {
  project                    = var.project_id
  dataset_id                 = var.dataset_id
  friendly_name              = var.dataset_description
  description                = var.dataset_description
  location                   = var.dataset_location
  delete_contents_on_destroy = var.delete_contents_on_destroy

  labels = {
    # Asumiendo que dataset_id tiene el formato app_env_suffix
    environment = split("_", var.dataset_id)[1]
    app         = split("_", var.dataset_id)[0]
  }
}

resource "google_bigquery_table" "tables" {
  for_each    = { for tbl in var.tables : tbl.table_id => tbl if fileexists(tbl.schema_path) } # Solo crea si el archivo de schema existe
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.dataset.dataset_id
  table_id    = each.value.table_id
  description = each.value.description != "" ? each.value.description : "Tabla ${each.value.table_id}"

  # Lee el schema desde un archivo JSON. El archivo debe contener un array de campos de BigQuery.
  # Ejemplo de schema.json:
  # [
  #   { "name": "user_id", "type": "STRING", "mode": "REQUIRED" },
  #   { "name": "preference", "type": "STRING", "mode": "NULLABLE" },
  #   { "name": "timestamp", "type": "TIMESTAMP", "mode": "NULLABLE" }
  # ]
  schema = file(each.value.schema_path)

  # Opcional: Configurar particionamiento y clustering
  # time_partitioning {
  #   type  = "DAY"
  #   field = "timestamp_column" # Nombre de la columna de timestamp para particionar
  # }
  # clustering = ["user_id_column"] # Lista de columnas para clustering

  deletion_protection = false # Poner a true en producción para tablas críticas

  depends_on = [google_bigquery_dataset.dataset]
}

# Advertencia si algún archivo de schema no existe
resource "null_resource" "schema_warnings" {
  for_each = { for tbl in var.tables : tbl.table_id => tbl if !fileexists(tbl.schema_path) }

  provisioner "local-exec" {
    command = "echo 'ADVERTENCIA: El archivo de schema ${each.value.schema_path} para la tabla ${each.key} no existe. La tabla no se creará con schema predefinido por Terraform.' >&2"
  }
}