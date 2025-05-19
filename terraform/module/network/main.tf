resource "google_vpc_access_connector" "connector" {
  project        = var.project_id
  region         = var.region
  name           = "${var.app_prefix}-vpc-connector"
  network        = var.network_name # Nombre de la red VPC (ej: "default" o "my-custom-vpc")
  ip_cidr_range  = var.ip_cidr_range # Rango /28 no solapado, ej: "10.8.0.0/28"
  min_throughput = var.min_throughput
  max_throughput = var.max_throughput

  # machine_type = "e2-micro" # Opcional, para conectores más pequeños/grandes
}