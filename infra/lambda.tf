module "monitoring_events_writer_lambda" {
  source                      = "<module_source_here>"
  namespace                   = var.namespace
  stage                       = var.stage
  lambda_function_name        = "monitoring-events-writer"
  lambda_function_description = "Events writer (ingestion monitoring benchmarks)"
  lambda_handler              = "src.main.writer_handler"
  runtime                     = "python3.8"
  memory_size                 = 128
  path_dummy_code             = "./lambda_dummy_code.zip"
  lambda_s3_bucket            = module.monitoring_ci_bucket.user_input_bucket_name_id
  role                        = module.monitoring_events_writer_lambda_role.role_arn

  env_variables = {
    RDS_DB_USER                    = aws_db_instance.monitoring_rds_db.username
    RDS_DB_HOST                    = aws_db_instance.monitoring_rds_db.address
    RDS_DB_NAME                    = aws_db_instance.monitoring_rds_db.name
    RDS_DB_PORT                    = aws_db_instance.monitoring_rds_db.port
    RDS_DB_PASSWORD                = aws_db_instance.monitoring_rds_db.password
    TS_TABLE_ID                    = aws_timestreamwrite_table.monitoring_events_ts_table.id
    CLOUDWATCH_LOG_GROUP           = aws_cloudwatch_log_group.monitoring_log_group.name
    ES_DOMAIN_URL                  = module.monitoring_es.domain_endpoint
    BENCHMARK_DATA_TABLE_NAME      = module.monitoring_dynamodb_table.table_name
  }

  depends_on = [
    aws_iam_policy.monitoring_events_writer_lambda_policy
  ]

  tags = {}
}

module "monitoring_events_reader_lambda" {
  source                      = "<module_source_here>"
  namespace                   = var.namespace
  stage                       = var.stage
  lambda_function_name        = "monitoring-events-reader"
  lambda_function_description = "Events reader (ingestion monitoring benchmarks)"
  lambda_handler              = "src.main.reader_handler"
  runtime                     = "python3.8"
  memory_size                 = 128
  path_dummy_code             = "./lambda_dummy_code.zip"
  lambda_s3_bucket            = module.monitoring_ci_bucket.user_input_bucket_name_id
  role                        = module.monitoring_events_reader_lambda_role.role_arn

  env_variables = {
    RDS_DB_USER               = aws_db_instance.monitoring_rds_db.username
    RDS_DB_HOST               = aws_db_instance.monitoring_rds_db.address
    RDS_DB_NAME               = aws_db_instance.monitoring_rds_db.name
    RDS_DB_PORT               = aws_db_instance.monitoring_rds_db.port
    RDS_DB_PASSWORD           = aws_db_instance.monitoring_rds_db.password
    TS_TABLE_ID               = aws_timestreamwrite_table.monitoring_events_ts_table.id
    CLOUDWATCH_LOG_GROUP      = aws_cloudwatch_log_group.monitoring_log_group.name
    ES_DOMAIN_URL             = module.monitoring_es.domain_endpoint
    BENCHMARK_DATA_TABLE_NAME = module.monitoring_dynamodb_table.table_name
  }

  depends_on = [
    aws_iam_policy.monitoring_events_reader_lambda_policy
  ]

  tags = {}
}
