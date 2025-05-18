variable "project_id" {
  description = "ID del proyecto GCP."
  type        = string
}

variable "region" {
  description = "Región GCP para el Conector VPC Access."
  type        = string
}

variable "app_prefix" {
  description = "Prefijo de la aplicación para nombrar el conector."
  type        = string
}

variable "network_name" {
  description = "Nombre de la red VPC a la que se conectará. Por defecto 'default'."
  type        = string
  default     = "default" # O el nombre de tu VPC personalizada
}

variable "ip_cidr_range" {
  description = "Rango IP CIDR /28 para el conector. Debe estar sin usar en la VPC."
  type        = string
  # Ejemplo: "10.8.0.0/28" - ¡ESTO DEBE SER ELEGIDO CUIDADOSAMENTE!
}

variable "min_throughput" {
  description = "Rendimiento mínimo del conector en Mbps (200-1000, incrementos de 100)."
  type        = number
  default     = 200
}

variable "max_throughput" {
  description = "Rendimiento máximo del conector en Mbps (debe ser >= min_throughput, 200-1000, incrementos de 100)."
  type        = number
  default     = 300
}