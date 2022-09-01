queries = {

    # ============================ Cloudwatch Insights ============================
    "cw": """
        stats count_distinct(job_id) by repo_id, bin(1m) as interval
        | filter stage = 'Finished'
                 and user_id in ["0011", "0111", "1111", "1110", "1100"]
        | sort interval desc
    """,

    # =============================== Elasticsearch ===============================
    "es": {
        "query": {
            "bool": {
                "must": [
                    {
                        "terms": {
                            "user_id": ["0011", "0111", "1111", "1110", "1100"]
                        }
                    },
                    {
                        "term": {
                            "stage": "Finished"
                        }
                    }
                ]
            }
        },
        "aggs": {
            "stats_per_batch": {
                "composite": {
                    "size": 100,
                    "sources": [
                        {
                            "interval": {
                                "date_histogram": {
                                    "field": "time",
                                    "calendar_interval": "1m",
                                    "order": "desc"
                                }
                            }
                        },
                        {
                            "repo": {
                                "terms": {
                                    "field": "repo_id"
                                }
                            }
                        }
                    ]
                },
                "aggregations": {
                    "num_finished_jobs": {
                        "cardinality": {
                            "field": "job_id",
                            "precision_threshold": 10000
                        }
                    }
                }
            }
        },
        "size": 0
    },

    # ================================ PostgresSQL ================================
    "rds": """
        SELECT repo_id,
               DATE_TRUNC('minute', time) AS interval,
               COUNT(DISTINCT(job_id)) AS num_jobs
        FROM monitoring_events
        WHERE stage = 'Finished'
              AND user_id IN ('0011', '0111', '1111', '1110', '1100')
        GROUP BY interval, repo_id
        ORDER BY interval DESC
    """,

    # ================================ Timestream =================================
    "ts": """
        SELECT repo_id,
               bin(time, 1m) AS interval,
               COUNT(DISTINCT(job_id)) AS num_jobs
        FROM "DataplatformPlayMonitoringV1"."MonitoringEvents"
        WHERE stage = 'Finished'
              AND user_id IN ('0011', '0111', '1111', '1110', '1100')
        GROUP BY repo_id, bin(time, 1m)
        ORDER BY bin(time, 1m) DESC
    """
}
