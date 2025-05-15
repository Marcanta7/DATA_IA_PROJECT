# Generate a random suffix for globally unique resource names like GCS buckets
resource "random_id" "resource_suffix" {
  byte_length = 4
}

# Define local variables for convenience and constructing names
locals {
  data_bucket_actual_name = "${var.data_bucket_name_prefix}${random_id.resource_suffix.hex}"
  # Use specific BQ location if provided, otherwise default to primary region
  effective_bigquery_location = var.bigquery_location != "" ? var.bigquery_location : var.gcp_region
}

# --- Module Instantiation ---

# 1. GCS Bucket Module
module "gcs_bucket" {
  source      = "./modules/gcs"           # Path to the GCS module directory
  project_id  = var.gcp_project_id
  region      = var.gcp_region
  bucket_name = local.data_bucket_actual_name # Pass the constructed unique name
}

# 2. BigQuery Module
module "bigquery_storage" {
  source     = "./modules/bigquery"      # Path to the BigQuery module directory
  project_id = var.gcp_project_id
  dataset_id = var.bigquery_dataset_id
  table_id   = var.bigquery_table_id
  location   = local.effective_bigquery_location # Use determined location
}

# 3. Cloud Run Service & Eventarc Trigger Module
module "csv_processing_service" {
  source                      = "./modules/cloud_run_service" # Path to the Cloud Run module
  project_id                  = var.gcp_project_id
  region                      = var.gcp_region
  service_name                = var.cloud_run_service_name
  container_image             = var.cloud_run_container_image # MUST be provided via tfvars
  gcs_bucket_name_for_trigger = local.data_bucket_actual_name # The bucket to watch
  eventarc_trigger_name       = var.eventarc_trigger_name
  bigquery_project_id         = var.gcp_project_id
  bigquery_dataset_id         = var.bigquery_dataset_id
  bigquery_table_id           = var.bigquery_table_id

  # Ensure underlying storage is created before setting up the service and trigger
  depends_on = [
    module.gcs_bucket,
    module.bigquery_storage
  ]
}

# --- Optional: Automatic CSV Upload Resources ---

# Upload the first CSV file if upload_initial_csv_files is true
resource "google_storage_bucket_object" "upload_csv_1" {
  count = var.upload_initial_csv_files ? 1 : 0 # Create only if variable is true

  name           = var.gcs_object_name_file1
  bucket         = local.data_bucket_actual_name
  source         = var.local_csv_file1_path # Local path from variable
  detect_md5hash = fileexists(var.local_csv_file1_path) ? filemd5(var.local_csv_file1_path) : ""

  # Ensure the bucket exists before trying to upload
  depends_on = [module.gcs_bucket]
}

# Upload the second CSV file if upload_initial_csv_files is true
resource "google_storage_bucket_object" "upload_csv_2" {
  count = var.upload_initial_csv_files ? 1 : 0 # Create only if variable is true

  name           = var.gcs_object_name_file2
  bucket         = local.data_bucket_actual_name
  source         = var.local_csv_file2_path # Local path from variable
  detect_md5hash = fileexists(var.local_csv_file2_path) ? filemd5(var.local_csv_file2_path) : ""

  # Ensure the bucket exists before trying to upload
  depends_on = [module.gcs_bucket]
}