resource "google_storage_bucket" "data_bucket" {
  name                        = var.bucket_name
  project                     = var.project_id
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true // Recommended for new buckets

  versioning {
    enabled = true // Good practice for data files
  }

  lifecycle_rule {
    condition {
      age = 90 // Example: delete objects older than 90 days
    }
    action {
      type = "Delete"
    }
  }
  # Add any other bucket configurations you need (e.g., logging)