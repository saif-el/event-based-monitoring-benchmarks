data "aws_iam_policy" "LambdaCloudwatchAccess" {
  arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_assume_role_policy_doc" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "lambda_eni_access_doc" {
  statement {
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DeleteNetworkInterface",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda_eni_access_policy" {
  name   = "${var.namespace}-${var.stage}-lambda-eni-access-policy"
  path   = "/${var.namespace}/"
  policy = data.aws_iam_policy_document.lambda_eni_access_doc.json
}

data "aws_iam_policy_document" "monitoring_events_writer_lambda_policy_doc" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:Query",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      module.monitoring_dynamodb_table.table_arn,
    ]
  }

  statement {
    effect  = "Allow"
    actions = ["es:*"]
    resources = [
      module.monitoring_es.domain_arn,
      "${module.monitoring_es.domain_arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "timestream:DescribeEndpoints",
      "timestream:WriteRecords",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "timestream:Select",
    ]
    resources = [
      aws_timestreamwrite_table.monitoring_events_ts_table.arn
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:DescribeLogStreams",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      aws_cloudwatch_log_group.monitoring_log_group.arn,
      "${aws_cloudwatch_log_group.monitoring_log_group.arn}:log-stream:*"
    ]
  }
}

resource "aws_iam_policy" "monitoring_events_writer_lambda_policy" {
  name   = "${var.namespace}-${var.stage}-monitoring-events-writer-lambda"
  path   = "/${var.namespace}/"
  policy = data.aws_iam_policy_document.monitoring_events_writer_lambda_policy_doc.json
}

data "aws_iam_policy_document" "monitoring_events_reader_lambda_policy_doc" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:DescribeTable",
      "dynamodb:GetItem",
      "dynamodb:Scan",
      "dynamodb:Query",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
    ]
    resources = [
      module.monitoring_dynamodb_table.table_arn,
    ]
  }

  statement {
    effect  = "Allow"
    actions = ["es:*"]
    resources = [
      module.monitoring_es.domain_arn,
      "${module.monitoring_es.domain_arn}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "timestream:DescribeEndpoints",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "timestream:Select",
    ]
    resources = [
      aws_timestreamwrite_table.monitoring_events_ts_table.arn
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:DescribeLogStreams",
      "logs:GetLogEvents",
      "logs:FilterLogEvents",
      "logs:StartQuery",
      "logs:GetQueryResults",
    ]
    resources = [
      aws_cloudwatch_log_group.monitoring_log_group.arn,
      "${aws_cloudwatch_log_group.monitoring_log_group.arn}:log-stream:*",
      "${aws_cloudwatch_log_group.monitoring_log_group.arn}::log-stream"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:StartQuery",
      "logs:GetQueryResults",
    ]
    resources = [
      "*"
    ]
  }
}

resource "aws_iam_policy" "monitoring_events_reader_lambda_policy" {
  name   = "${var.namespace}-${var.stage}-monitoring-events-reader-lambda"
  path   = "/${var.namespace}/"
  policy = data.aws_iam_policy_document.monitoring_events_reader_lambda_policy_doc.json
}
