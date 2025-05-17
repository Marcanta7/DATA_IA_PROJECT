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