# ---------------------------------------------------------------
# General GCP Configuration
# ---------------------------------------------------------------
variable "gcp_project_id" {
  description = "REQUIRED: The GCP project ID to deploy resources into."
  type        = string
  # No default - must be provided by the user
}

variable "gcp_region" {
  description = "The primary GCP region for deploying regional resources like Cloud Run, GCS Bucket, Eventarc."
  type        = string
  default     = "europe-southwest1" # Default region, can be overridden in tfvars
}

# ---------------------------------------------------------------
# GCS Bucket Configuration
# ---------------------------------------------------------------
variable "data_bucket_name_prefix" {
  description = "Prefix for the GCS data bucket name. A random suffix will be added for uniqueness."
  type        = string
  default     = "csv-input-data-"
}

# ---------------------------------------------------------------
# Cloud Run Service Configuration
# ---------------------------------------------------------------
variable "cloud_run_service_name" {
  description = "Name for the Cloud Run service that will perform CSV matching."
  type        = string
  default     = "csv-matcher-service"
}

variable "cloud_run_container_image" {
  description = "REQUIRED: The full path to the Docker container image for the Cloud Run service (e.g., 'gcr.io/PROJECT_ID/SERVICE_NAME:TAG' or 'us-central1-docker.pkg.dev/PROJECT_ID/REPO/SERVICE_NAME:TAG')."
  type        = string
  # No default - must be provided by the user after building/pushing the image.
}

# ---------------------------------------------------------------
# BigQuery Configuration
# ---------------------------------------------------------------
variable "bigquery_dataset_id" {
  description = "ID for the BigQuery dataset where matched results will be stored."
  type        = string
  default     = "csv_processing_results"
}

variable "bigquery_table_id" {
  description = "ID for the BigQuery table within the dataset to store matched data."
  type        = string
  default     = "matched_data"
}

variable "bigquery_location" {
  description = "Location for the BigQuery dataset (e.g., 'US', 'EU', 'asia-northeast1'). Defaults to the primary gcp_region."
  type        = string
  default     = "" # An empty string will default to var.gcp_region in the main.tf logic
}

# ---------------------------------------------------------------
# Eventarc Configuration
# ---------------------------------------------------------------
variable "eventarc_trigger_name" {
  description = "Name for the Eventarc trigger listening to GCS uploads."
  type        = string
  default     = "gcs-csv-upload-cloudrun-trigger"
}

# ---------------------------------------------------------------
# Automatic CSV Upload Configuration (Optional Initialization)
# ---------------------------------------------------------------
variable "upload_initial_csv_files" {
  description = "Set to true to automatically upload the specified local CSV files during 'terraform apply'."
  type        = bool
  default     = true # Set to false if you don't want Terraform to upload initial files
}

variable "local_csv_file1_path" {
  description = "Path to the first local CSV file to upload if 'upload_initial_csv_files' is true."
  type        = string
  default     = "./data/reference_data.csv" # Example default path
}

variable "gcs_object_name_file1" {
  description = "Desired object name for the first CSV file in GCS."
  type        = string
  default     = "reference_data.csv" # Example name in GCS
}

variable "local_csv_file2_path" {
  description = "Path to the second local CSV file to upload if 'upload_initial_csv_files' is true."
  type        = string
  default     = "./data/input_data_batch_001.csv" # Example default path
}

variable "gcs_object_name_file2" {
  description = "Desired object name for the second CSV file in GCS."
  type        = string
  default     = "input_data_batch_001.csv" # Example name in GCS
}