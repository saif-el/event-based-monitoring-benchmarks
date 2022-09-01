module "monitoring_ci_bucket" {
  source                        = "<module_source_here>"
  namespace                     = var.namespace
  stage                         = var.stage
  name                          = "monitoring-ci-bucket"
  enable_s3_public_access_block = true
  enable_versioning             = false
  lifecycle_rules               = []
  enable_bucket_key             = true

  tags = {}
}
