module "monitoring_es" {
  source                    = "<module_source_here>"
  name                      = "monitoring"
  stage                     = var.stage
  namespace                 = var.namespace
  es_version                = "7.10"
  enable_ebs                = "true"
  es_volume_type            = "gp2"
  es_volume_size            = "20"
  es_access_policy          = data.aws_iam_policy_document.monitoring_es_access_policy_doc.json
  es_instance_type          = "r6g.large.elasticsearch"
  es_instance_count         = 1
  es_enable_encrypt_at_rest = "false"
  vpc_enabled               = false
}

data "aws_iam_policy_document" "monitoring_es_access_policy_doc" {
  statement {
    actions = ["es:*"]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    resources = ["${module.monitoring_es.domain_arn}/*"]
    condition {
      test     = "IpAddress"
      variable = "aws:SourceIp"
      values   = ["*"]
    }
  }
}
