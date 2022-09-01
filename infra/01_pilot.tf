provider "aws" {
  region = var.region
  default_tags {
    tags = {
      "${var.default_tag_microservice_key}" = var.microservice_name
      "${var.benchmark_tag_key}"            = var.ingestion_monitoring_benchmark_name
    }
  }
}

terraform {
  backend "local" {
    path = "./terraform.tfstate"
  }
}
