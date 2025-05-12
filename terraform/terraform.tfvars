# ---------------------------------------------------------------
# General GCP Configuration - ** REQUIRED **
# ---------------------------------------------------------------
gcp_project_id = "diap3-458416" # Replace with your Project ID

# Optional: Override default region if needed
# gcp_region     = "europe-west1"

# ---------------------------------------------------------------
# GCS Bucket Configuration - Optional Overrides
# ---------------------------------------------------------------
# data_bucket_name_prefix = "my-company-csv-input-"

# ---------------------------------------------------------------
# Cloud Run Service Configuration - ** REQUIRED IMAGE **
# ---------------------------------------------------------------
# cloud_run_service_name = "my-csv-processor"

# Replace with the actual path to your built container image in GCR or Artifact Registry
cloud_run_container_image = "gcr.io/your-gcp-project-id-here/csv-matcher:latest"
# OR Example for Artifact Registry: "us-central1-docker.pkg.dev/your-gcp-project-id-here/my-repo/csv-matcher:v1.0.1"

# ---------------------------------------------------------------
# BigQuery Configuration - Optional Overrides
# ---------------------------------------------------------------
# bigquery_dataset_id = "production_matching_output"
# bigquery_table_id   = "matched_transactions"
# bigquery_location   = "US" # Example: Use multi-region for BQ

# ---------------------------------------------------------------
# Eventarc Configuration - Optional Overrides
# ---------------------------------------------------------------
# eventarc_trigger_name = "prod-gcs-trigger"

# ---------------------------------------------------------------
# Automatic CSV Upload Configuration - ** CHECK PATHS **
# ---------------------------------------------------------------
# Set to false if you don't want Terraform to upload files on 'apply'
# upload_initial_csv_files = false

# ** REQUIRED IF upload_initial_csv_files = true **
# Update these paths to point to your actual local CSV files
local_csv_file1_path = "./local_data_files/my_reference_dataset.csv"
gcs_object_name_file1  = "reference_data/current_dataset.csv" # Example: Upload into a 'folder'

local_csv_file2_path = "./local_data_files/batch_today.csv"
gcs_object_name_file2  = "inputs/daily_batch.csv" # Example: Upload into a 'folder'