queries = {

    # ============================ Cloudwatch Insights ============================
    "cw": """
        stats earliest(created_at) as created_at_,
              latest(@timestamp) as last_updated_at,
              count_distinct(job_id) as num_jobs,
              sum(finished) as successful_jobs,
              sum(errored) as errored_jobs
              by ingestion_batch_id
        | limit 100
    """,

    # =============================== Elasticsearch ===============================
    "es": {
        "aggs": {
            "stats_per_batch": {
                "composite": {
                    "size": 100,
                    "sources": [
                        {
                            "batch": {
                                "terms": {
                                    "field": "ingestion_batch_id"
                                }
                            }
                        }
                    ]
                },
                "aggs": {
                    "created_at": {
                        "min": {
                            "field": "created_at"
                        }
                    },
                    "last_updated_at": {
                        "max": {
                            "field": "time"
                        }
                    },
                    "num_jobs": {
                        "cardinality": {
                            "field": "job_id",
                            "precision_threshold": 10000
                        }
                    },
                    "successful_jobs": {
                        "sum": {
                            "field": "finished"
                        }
                    },
                    "failed_jobs": {
                        "sum": {
                            "field": "errored"
                        }
                    }
                }
            }
        },
        "size": 0
    },

    # ================================ PostgresSQL ================================
    "rds": """
        WITH m1 AS (
            SELECT DISTINCT(ingestion_batch_id) AS ingestion_batch_id
            FROM monitoring_events
            LIMIT 100
        )
        SELECT m2.*
        FROM m1
        INNER JOIN LATERAL (
            SELECT ingestion_batch_id,
                   COUNT(DISTINCT(job_id)) AS num_jobs,
                   SUM(CAST(finished AS integer)) AS successful_jobs,
                   SUM(CAST(errored AS integer)) AS errored_jobs,
                   MIN(created_at) AS creation_time,
                   MAX(time) AS last_updation_time
            FROM monitoring_events
            WHERE ingestion_batch_id = m1.ingestion_batch_id
            GROUP BY ingestion_batch_id
        ) AS m2 ON true
    """,

    # ================================ Timestream =================================
    "ts": """
        SELECT ingestion_batch_id,
               COUNT(DISTINCT(job_id)) AS num_jobs,
               SUM(CAST(finished AS integer)) AS successful_jobs,
               SUM(CAST(errored AS integer)) AS errored_jobs,
               MIN(created_at) AS creation_time,
               MAX(time) AS last_updation_time
        FROM "DataplatformPlayMonitoringV1"."MonitoringEvents"
        GROUP BY ingestion_batch_id
        LIMIT 100
    """
}
