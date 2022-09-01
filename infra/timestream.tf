resource "aws_timestreamwrite_database" "monitoring_ts_db" {
  database_name = "${title(var.namespace)}${title(var.stage)}MonitoringV1"
}

resource "aws_timestreamwrite_table" "monitoring_events_ts_table" {
  database_name = aws_timestreamwrite_database.monitoring_ts_db.database_name
  table_name    = "MonitoringEvents"

  retention_properties {
    memory_store_retention_period_in_hours  = 168 # 7 days
    magnetic_store_retention_period_in_days = 7
  }
}
