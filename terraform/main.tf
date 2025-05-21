

# module artifact_registry
module "artifact_registry" {
  source = "./module/artifact_registry"

  project_id = var.project_id
  region     = var.region
  reponame = var.reponame
  repositories = var.artifact_registry_repositories
}

# module gcp-function
module "function_build" {
  source = "./module/gcp-function"

  project_id              = var.project_id
  region                  = var.region
  reponame                = var.reponame
  cloud_run_service_name  = var.cloud_run_service_name
  image_name              = var.image_name
}

# module bigquery
module "bigquery" {
  source = "./module/bigquery"

  project_id = var.project_id
  dataset_id = var.dataset_id
  table_id   = var.table_id
}

# module firestore

resource "google_project_service" "appengine" {
  project = var.project_id
  service = "appengine.googleapis.com"
}

module "firestore" {
  source                    = "./module/firestore"
  project_id                = var.project_id
  location_id               = var.location
  database_type             = var.firestore_database_type
  app_engine_api_dependency = google_project_service.appengine.app_engine_api_dependency
}

# module gcs
module "gcs" {
  source = "./module/gcs"

  project_id = var.project_id
  bucket_name = var.bucket_name
  location    = var.location
  force_destroy = var.enable_force_destroy_gcs_bucket
}

# module cloud_run
module "cloud_run" {
  source = "./module/cloud_run"

  project_id                = var.project_id
  region                   = var.region
  service_name             = var.cloud_run_service_name
  container_port           = var.container_port
  memory                   = var.memory
  cpu                      = var.cpu
  min_instances            = var.min_instances
  max_instances            = var.max_instances
  allow_unauthenticated    = var.allow_unauthenticated
  service_account_email = module.iam.service_account_email
  container_image = module.artifact_registry.container_image
}

# module iam
module "iam" {
  source = "./module/iam"

  project_id = var.project_id
  region = var.region
  app_prefix = var.app_prefix
  cloud_run_service_account_suffixes = var.cloud_run_service_account_suffixes
}


# module network
module "network" {
  source = "./module/network"

  project_id = var.project_id
  region     = var.region
  ip_cidr_range      = var.vpc_connector_ip_cidr_range
  app_prefix = var.app_prefix
}

