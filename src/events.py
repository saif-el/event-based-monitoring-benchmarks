import uuid
import random
from dataclasses import dataclass
from enum import Enum
from random import choice

from faker import Faker

from src.helpers import get_unix_timestamp, get_unix_timestamp_ms, DataType

fake = Faker()
Faker.seed(0)
org_ids = ("1", "2")
user_ids_for_org_id = {
    "1": (
        "0011",
        "0111",
        "1111",
        "1110",
        "1100",
    ),
    "2": (
        "0001",
        "1000",
    ),
}
fractions = (0.1, 0.25, 0.5)
failure_rates = (0.0, 0.0001, 0.01)
repo_ids = ("16311212173", "16554252419", "16629121578")
priorities = ("HIGH", "MEDIUM", "LOW")
job_types = ("ADD", "UPDATE", "DELETE")


class IngestionJobStage(int, Enum):
    IN_QUEUE = 0
    PROCESSING_FILE_CONTENTS_PT_1 = 1
    PROCESSING_FILE_METADATA_PT_1 = 2
    STAGED = 3
    PROCESSING_FILE_CONTENTS_PT_2 = 4
    PROCESSING_FILE_METADATA_PT_2 = 5
    FINISHED = 6

    def _name_for_stage(self):
        stage_names = {
            0: "In-queue",
            1: "Processing file contents, Part I",
            2: "Processing file metadata, Part I",
            3: "Staged",
            4: "Processing file contents, Part II",
            5: "Processing file metadata, Part II",
            6: "Finished",
        }
        return stage_names.get(self.value)

    def __str__(self):
        return self._name_for_stage()

    def stage_num(self):
        return self.value

    def next_stage(self):
        if self >= IngestionJobStage.FINISHED:
            return self
        return IngestionJobStage(self.value + 1)


@dataclass
class IngestionBatch:
    batch_id: str
    org_id: str
    user_id: str
    repo_id: str
    repo_version: str
    priority: str
    num_jobs: int
    job_failure_rate: float
    created_at: int


class IngestionEvent:

    def __init__(self, ingestion_batch: IngestionBatch):
        self.ingestion_batch = ingestion_batch
        self.job_id = str(uuid.uuid4())
        self.job_type = choice(job_types)
        self.dataset_id = f"{fake.pystr(6, 6).upper()}_{fake.pystr(4, 4).upper()}"
        self.num_stages = IngestionJobStage.FINISHED.stage_num()
        self.time = get_unix_timestamp_ms()
        self.stage = IngestionJobStage.IN_QUEUE
        self.stage_progress = self.stage.value
        self.errored = False
        self.finished = False

    def as_dict(self):
        return {
            "ingestion_batch_id": self.ingestion_batch.batch_id,
            "org_id": self.ingestion_batch.org_id,
            "user_id": self.ingestion_batch.user_id,
            "repo_id": self.ingestion_batch.repo_id,
            "repo_version": self.ingestion_batch.repo_version,
            "priority": self.ingestion_batch.priority,
            "job_id": self.job_id,
            "job_type": self.job_type,
            "created_at": self.ingestion_batch.created_at,
            "dataset_id": self.dataset_id,
            "num_stages": self.num_stages,
            "time": self.time,
            "stage": str(self.stage),
            "stage_progress": self.stage_progress,
            "errored": self.errored,
            "finished": self.finished,
        }

    def transition_to_next_stage(self):
        self.time = get_unix_timestamp_ms()
        self.stage = self.stage.next_stage()
        self.stage_progress = self.stage.value
        if self.stage != IngestionJobStage.FINISHED:
            self.errored = (random.random() < self.ingestion_batch.job_failure_rate)
        else:
            self.finished = True

    @staticmethod
    def get_types_for_event_fields():
        field_types = {
            "ingestion_batch_id": DataType.STRING,
            "org_id": DataType.STRING,
            "user_id": DataType.STRING,
            "repo_id": DataType.STRING,
            "repo_version": DataType.STRING,
            "priority": DataType.STRING,
            "job_id": DataType.STRING,
            "job_type": DataType.STRING,
            "created_at": DataType.TIMESTAMP,
            "dataset_id": DataType.STRING,
            "num_stages": DataType.INTEGER,
            "time": DataType.TIMESTAMP,
            "stage": DataType.STRING,
            "stage_progress": DataType.INTEGER,
            "errored": DataType.BOOLEAN,
            "finished": DataType.BOOLEAN,
        }
        return field_types.copy()


def generate_ingestion_job_events(ingestion_batch: IngestionBatch):
    job_events = []
    for _ in range(ingestion_batch.num_jobs):
        job_events.append(IngestionEvent(ingestion_batch))
    return job_events


def generate_ingestion_batch_pair(min_num_jobs, max_num_jobs):
    org_id = choice(org_ids)
    user_ids = user_ids_for_org_id.get(org_id)
    first_user_id = choice(user_ids)
    second_user_id = choice(user_ids)

    repo_id = choice(repo_ids)
    repo_version = str(get_unix_timestamp())
    priority = choice(priorities)

    first_ingestion_batch_id = f"{repo_id}__{repo_version}__{first_user_id}"
    second_ingestion_batch_id = f"{repo_id}__{repo_version}__{second_user_id}"

    num_jobs = random.randint(min_num_jobs, max_num_jobs)
    job_split = choice(fractions)
    num_first_user_jobs = int(num_jobs * job_split)
    num_second_user_jobs = num_jobs - num_first_user_jobs

    ir1 = IngestionBatch(
        first_ingestion_batch_id,
        org_id,
        first_user_id,
        repo_id,
        repo_version,
        priority,
        num_first_user_jobs,
        random.choice(failure_rates),
        get_unix_timestamp_ms(),
    )
    ir2 = IngestionBatch(
        second_ingestion_batch_id,
        org_id,
        second_user_id,
        repo_id,
        repo_version,
        priority,
        num_second_user_jobs,
        random.choice(failure_rates),
        get_unix_timestamp_ms(),
    )

    return ir1, ir2
