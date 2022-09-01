from src.events import (
    IngestionJobStage,
    generate_ingestion_job_events,
    generate_ingestion_batch_pair
)
from src.write_helpers import write_events
from src.query_helpers import perform_queries


def writer_handler(_event, _context):
    batch_1, batch_2 = generate_ingestion_batch_pair(6000, 8000)
    batch_1_job_events = generate_ingestion_job_events(batch_1)
    batch_2_job_events = generate_ingestion_job_events(batch_2)

    for job_events in [batch_1_job_events, batch_2_job_events]:
        num_stages = IngestionJobStage.FINISHED + 1
        errored_jobs = set()
        for i in range(num_stages):
            events = [
                job.as_dict()
                for job in job_events
                if job.job_id not in errored_jobs
            ]
            write_events(events)

            for job_event in job_events:
                if job_event.errored:
                    errored_jobs.add(job_event.job_id)
                    continue
                job_event.transition_to_next_stage()

    return {"num_jobs": batch_1.num_jobs + batch_2.num_jobs}


def reader_handler(event, _context):
    scale = event.get("scale")
    perform_queries(scale)
