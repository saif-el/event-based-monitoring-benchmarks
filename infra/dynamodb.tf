module "monitoring_dynamodb_table" {
  source    = "<module_source_here>"
  namespace = var.namespace
  stage     = var.stage
  name      = "monitoring"
  hash_key  = "operation"
  range_key  = "record_id"
  dynamodb_attributes = [
    {
      name = "operation"
      type = "S"
    },
    {
      name = "record_id"
      type = "S"
    }
  ]

  billing_mode                 = "PROVISIONED"
  read_capacity                = 5
  write_capacity               = 5
  enable_autoscaler            = true
  autoscale_min_read_capacity  = 5
  autoscale_max_read_capacity  = 200
  autoscale_read_target        = 50
  autoscale_min_write_capacity = 5
  autoscale_max_write_capacity = 200
  autoscale_write_target       = 50

  tags = {}
}
