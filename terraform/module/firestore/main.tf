# Firestore requiere que una aplicación App Engine exista en el proyecto para definir la ubicación.
# Si ya existe una, este recurso la adoptará o dará error si la ubicación es incompatible.
# Si no existe, creará una aplicación ligera.
resource "google_app_engine_application" "app" {
  project       = var.project_id
  location_id   = var.location_id # Esto fija la ubicación de Firestore y el bucket GCS por defecto del proyecto
  database_type = var.database_type

  # Depende de que la API de App Engine esté habilitada
  depends_on = [var.app_engine_api_dependency]
}

# Este recurso provisiona la base de datos Firestore.
# En modo NATIVO, solo puede haber una base de datos "(default)" por proyecto.
# Este módulo activa Firestore en la ubicación especificada a través de App Engine.
resource "google_firestore_database" "database" {
  provider    = google-beta # El recurso google_firestore_database está en el proveedor beta
  project     = var.project_id
  name        = "(default)" # En modo NATIVO, siempre es "(default)"
  location_id = google_app_engine_application.app.location_id # Usa la ubicación fijada por App Engine
  type        = var.database_type

  # delete_protection_state = "DELETE_PROTECTION_ENABLED" # Considera habilitar en producción

  # Asegura que la aplicación App Engine se cree primero
  depends_on = [google_app_engine_application.app]
}

# Puedes definir índices de Firestore aquí si los necesitas. Ejemplo:
/*
resource "google_firestore_index" "idx_users_by_email" {
  project     = var.project_id
  database    = google_firestore_database.database.name # Debería ser "(default)"
  collection  = "users" # El grupo de colección al que aplica el índice
  query_scope = "COLLECTION" # O "COLLECTION_GROUP"

  fields {
    field_path = "email"
    order      = "ASCENDING"
  }
  # fields { # Para índices compuestos
  #   field_path = "last_active"
  #   order      = "DESCENDING"
  # }

  depends_on = [google_firestore_database.database]
}
*/