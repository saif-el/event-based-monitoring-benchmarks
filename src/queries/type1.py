queries = {

    # ============================ Cloudwatch Insights ============================
    "cw": """
        fields ingestion_batch_id
        | stats count(*) as unique_events by ingestion_batch_id
        | limit 100
    """,

    # =============================== Elasticsearch ===============================
    "es": {
        "aggs": {
            "events_per_batch": {
                "composite": {
                    "size": 100,
                    "sources": [
                        {"batch": {"terms": {"field": "ingestion_batch_id"}}}
                    ]
                }
            }
        },
        "size": 0
    },

    # ================================ PostgresSQL ================================
    "rds": """
        SELECT ingestion_batch_id, COUNT(*)
        FROM monitoring_events
        GROUP BY ingestion_batch_id
        LIMIT 100
    """,

    # ================================ Timestream =================================
    "ts": """
        SELECT ingestion_batch_id, COUNT(*)
        FROM "DataplatformPlayMonitoringV1"."MonitoringEvents"
        GROUP BY ingestion_batch_id
        LIMIT 100
    """
}
