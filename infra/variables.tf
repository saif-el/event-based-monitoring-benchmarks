variable "region" {
  description = "AWS Resource Region"
  type        = string
}

variable "namespace" {
  description = "AWS namespace"
  type        = string
}

variable "stage" {
  description = "AWS deployement"
  type        = string
}

variable "default_tag_microservice_key" {
  description = "Microservice tag"
  type        = string
}

variable "microservice_name" {
  description = "Microservice name"
  type        = string
}

variable "benchmark_tag_key" {
  description = "Benchmark key"
  type        = string
}

variable "ingestion_monitoring_benchmark_name" {
  description = "Ingestion monitoring benchmark name"
  type        = string
}
