variable "project_id" {
  description = "The GCP project ID."
  type        = string
}

variable "region" {
  description = "The GCP region for the bucket."
  type        = string
}

variable "dataset_id" {
  description = "Name for the dataset."
  type        = string
}

variable "location" {
  description = "Location of dataset."
  type        = string
}

variable "table_id" {
  description = "name for the table."
  type        = string
}