resource "google_cloud_run_v2_service" "order_service" {
  name     = "order-service"
  location = "us-central1"
}

resource "google_cloud_run_v2_service" "payment_service" {
  name     = "payment-service"
  location = "us-central1"
}

resource "google_sql_database_instance" "orders_db" {
  name             = "orders-db"
  database_version = "POSTGRES_15"
  region           = "us-central1"

  settings {
    tier = "db-f1-micro"
  }
}

resource "google_pubsub_topic" "orders_topic" {
  name = "orders-topic"
}

resource "google_storage_bucket" "architecture_files" {
  name     = "archguard-example-files"
  location = "US"
}