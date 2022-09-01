resource "aws_db_instance" "monitoring_rds_db" {
  allocated_storage   = 30
  engine              = "postgres"
  engine_version      = "13.7"
  instance_class      = "db.t3.medium"
  identifier          = "${var.namespace}-${var.stage}-monitoring-v1"
  db_name             = "monitoring_events"
  username            = "play"
  password            = "pingpong"
  port                = "5432"
  publicly_accessible = true
  skip_final_snapshot = true
}
