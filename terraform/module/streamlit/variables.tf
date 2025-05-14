variable "gcp_project_id" {
  description = "REQUIRED: The GCP project ID to deploy resources into."
  type        = string
  # No default - must be provided by the user
}

variable "gcp_region" {
  description = "The primary GCP region for deploying regional resources like Cloud Run, GCS Bucket, Eventarc."
  type        = string

}

variable "image_name_streamlit" {
  description = "Nombre de la imagen de Docker de Streamlit"
  type        = string
}