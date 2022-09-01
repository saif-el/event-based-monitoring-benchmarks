module "monitoring_events_writer_lambda_role" {
  source             = "<module_source_here>"
  namespace          = var.namespace
  stage              = var.stage
  role_name          = "monitoring-events-writer-lambda-role"
  region             = var.region
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy_doc.json
  number_of_policies = 3
  custom_role_policy_arns = [
    data.aws_iam_policy.LambdaCloudwatchAccess.arn,
    aws_iam_policy.lambda_eni_access_policy.arn,
    aws_iam_policy.monitoring_events_writer_lambda_policy.arn,
  ]

  tags = {}
}

module "monitoring_events_reader_lambda_role" {
  source             = "<module_source_here>"
  namespace          = var.namespace
  stage              = var.stage
  role_name          = "monitoring-events-reader-lambda-role"
  region             = var.region
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role_policy_doc.json
  number_of_policies = 3
  custom_role_policy_arns = [
    data.aws_iam_policy.LambdaCloudwatchAccess.arn,
    aws_iam_policy.lambda_eni_access_policy.arn,
    aws_iam_policy.monitoring_events_reader_lambda_policy.arn,
  ]

  tags = {}
}
