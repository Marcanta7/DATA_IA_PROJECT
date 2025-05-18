gcp_project_id = "diap3-458416"
gcp_region     = "europe-west1"
gcp_zone       = "europe-west1-b"
app_name       = "ai-diet-prod" # O el nombre que prefieras
environment    = "prod"         # O dev, staging

# Opcional: Sobrescribir valores por defecto
# firestore_location_id = "eur3"
# bigquery_location = "EU"
# enable_force_destroy_gcs_bucket = true # Solo para dev/test

# cloud_run_api_settings = {
#   image_name                = "my-custom-api"
#   container_port            = 8080
#   memory                    = "1Gi"
#   cpu                       = "1"
#   min_instances             = 1
#   max_instances             = 5
#   allow_unauthenticated     = true
#   service_account_name_suffix = "custom-api-sa"
# }

# enable_vpc_connector = true
# vpc_connector_ip_cidr_range = "10.10.0.0/28" # Un rango libre en tu VPC