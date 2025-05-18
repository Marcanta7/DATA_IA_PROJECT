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

# Define structure for clean enriched table
resource "google_bigquery_table" "clean_enriched_table" {
  dataset_id = google_bigquery_dataset.food_data.dataset_id
  table_id   = "mercadona_enriched_clean"
  project    = var.project_id
  
  deletion_protection = false

  # Use the same schema as the original table
  schema = file("${path.module}/schema.json")
}

# Create a stored procedure to populate the clean table
resource "google_bigquery_routine" "populate_clean_table" {
  dataset_id = google_bigquery_dataset.food_data.dataset_id
  routine_id = "sp_populate_clean_table"
  routine_type = "PROCEDURE"
  language = "SQL"
  project = var.project_id

  definition_body = <<-EOQ
    BEGIN
      -- Clear any existing data
      DELETE FROM `${var.project_id}.${var.dataset_id}.mercadona_enriched_clean` WHERE 1=1;
      
      -- Insert only enriched records
      INSERT INTO `${var.project_id}.${var.dataset_id}.mercadona_enriched_clean`
      SELECT *
      FROM `${var.project_id}.${var.dataset_id}.${var.table_id}`
      WHERE off_product_name IS NOT NULL 
        AND off_product_name != ''
        AND off_product_name != 'N/A';
    END
  EOQ

  depends_on = [
    google_bigquery_table.products,
    google_bigquery_table.clean_enriched_table
  ]
}

# Create a query job to execute the stored procedure once
resource "null_resource" "execute_procedure" {
  provisioner "local-exec" {
    command = <<EOT
      bq query --location=${var.location} --use_legacy_sql=false \
      'CALL `${var.project_id}.${var.dataset_id}.sp_populate_clean_table`();'
    EOT
  }

  depends_on = [
    google_bigquery_routine.populate_clean_table
  ]

  # This ensures the procedure runs on every apply
  # If you want it to run only once, remove these triggers
  triggers = {
    always_run = "${timestamp()}"
  }
}

# View for easily accessing enriched products
resource "google_bigquery_table" "enriched_products_view" {
  dataset_id = google_bigquery_dataset.food_data.dataset_id
  table_id   = "v_mercadona_enriched_only"
  project    = var.project_id

  deletion_protection = false

  view {
    query = <<-EOQ
      SELECT *
      FROM `${var.project_id}.${var.dataset_id}.${var.table_id}`
      WHERE off_product_name IS NOT NULL 
        AND off_product_name != ''
        AND off_product_name != 'N/A'
    EOQ
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.products]
}