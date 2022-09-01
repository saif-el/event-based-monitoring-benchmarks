queries = {

    # ============================ Cloudwatch Insights ============================
    "cw": """
        filter ingestion_batch_id = "16554252419__1661749456__1110"
        | stats latest(stage) as latest_stage,
                latest(stage_progress) as latest_progress,
                latest(errored) as did_error
                by ingestion_batch_id, job_id
    """,

    # =============================== Elasticsearch ===============================
    "es": {
        "query": {
            "term": {
                "ingestion_batch_id": "16554252419__1661749456__1110"
            }
        },
        "aggs": {
            "stats_per_batch": {
                "composite": {
                    "size": 100,
                    "sources": [
                        {
                            "batch": {
                                "terms": {
                                    "field": "job_id"
                                }
                            }
                        }
                    ]
                },
                "aggregations": {
                    "latest_job_status": {
                        "top_hits": {
                            "docvalue_fields": [
                                "time"
                            ],
                            "_source": [
                                "stage",
                                "stage_progress",
                                "errored"
                            ],
                            "size": 1,
                            "sort": [
                                {
                                    "time": {
                                        "order": "desc"
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        },
        "size": 0
    },

    # ================================ PostgresSQL ================================
    "rds": """
        WITH j1 AS (
            SELECT DISTINCT(job_id) AS job_id
            FROM monitoring_events
            WHERE ingestion_batch_id = '16554252419__1661749456__1110'
        )
        SELECT j2.*
        FROM j1
        INNER JOIN LATERAL (
                SELECT job_id,
                       stage,
                       stage_progress,
                       errored,
                       time AS last_updation_time
                FROM monitoring_events
                WHERE job_id = j1.job_id
                ORDER BY time DESC
                LIMIT 1
        ) AS j2 ON true
    """,

    # ================================ Timestream =================================
    "ts": """
        SELECT job_id,
              max_by(stage, time) AS stage,
              max_by(stage_progress, time) AS stage_progress,
              max_by(errored, time) AS errored,
              max(time) AS last_updation_time
        FROM "DataplatformPlayMonitoringV1"."MonitoringEvents"
        WHERE ingestion_batch_id = '16554252419__1661749456__1110'
        GROUP BY job_id
    """
}
