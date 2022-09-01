resource "aws_cloudwatch_log_group" "monitoring_log_group" {
  name = "${var.namespace}-${var.stage}-monitoring-v1"
}
