variable "project_id" {
  description = "The GCP project ID."
  type        = string
}

variable "region" {
  description = "The GCP region for the bucket."
  type        = string
}

variable "bucket_name" {
  description = "Name for the GCS data bucket."
  type        = string
}