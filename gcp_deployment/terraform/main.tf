terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west1"
}

# BigQuery Dataset
resource "google_bigquery_dataset" "similarweb_dataset" {
  dataset_id                  = "similarweb_data"
  friendly_name              = "SimilarWeb Data"
  description                = "Dataset for SimilarWeb extracted data"
  location                   = "EU"
  default_table_expiration_ms = null

  labels = {
    env = "production"
  }
}

# BigQuery Tables
resource "google_bigquery_table" "segments_data" {
  dataset_id = google_bigquery_dataset.similarweb_dataset.dataset_id
  table_id   = "segments_data"

  time_partitioning {
    type  = "DAY"
    field = "extraction_date"
  }

  schema = file("../bigquery_schemas/segments_schema.json")
}

resource "google_bigquery_table" "websites_data" {
  dataset_id = google_bigquery_dataset.similarweb_dataset.dataset_id
  table_id   = "websites_data"

  time_partitioning {
    type  = "DAY"
    field = "extraction_date"
  }

  schema = file("../bigquery_schemas/websites_schema.json")
}

# Cloud Storage Bucket
resource "google_storage_bucket" "data_bucket" {
  name          = "${var.project_id}-similarweb-data"
  location      = "EU"
  force_destroy = false

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

# Cloud Function
resource "google_cloudfunctions_function" "extraction_function" {
  name        = "similarweb-daily-extraction"
  description = "Daily extraction of SimilarWeb data"
  runtime     = "python311"

  available_memory_mb   = 512
  source_archive_bucket = google_storage_bucket.gcf_source.name
  source_archive_object = google_storage_bucket_object.function_source.name
  trigger_http          = true
  entry_point          = "similarweb_extraction"
  timeout              = 540  # 9 minutes

  environment_variables = {
    SIMILARWEB_API_KEY = var.similarweb_api_key
    GCP_PROJECT_ID     = var.project_id
    BIGQUERY_DATASET   = google_bigquery_dataset.similarweb_dataset.dataset_id
  }
}

# Cloud Scheduler Job
resource "google_cloud_scheduler_job" "daily_extraction" {
  name             = "similarweb-daily-extraction-scheduler"
  description      = "Trigger daily SimilarWeb data extraction"
  schedule         = "0 2 * * *"  # Every day at 2 AM
  time_zone        = "Europe/Paris"
  attempt_deadline = "600s"

  http_target {
    http_method = "GET"
    uri         = google_cloudfunctions_function.extraction_function.https_trigger_url
  }
}
