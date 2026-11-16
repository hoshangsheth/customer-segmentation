"""
In-memory store for uploads and their analyses. Nothing is written to disk; jobs expire after a TTL
and the oldest are evicted beyond a cap, so memory stays bounded.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

import pandas as pd

from customer_segmentation.batch.analyze import Analysis


@dataclass
class Job:
    id: str
    frames: dict[str, pd.DataFrame]
    filenames: dict[str, str]
    sample: bool = False
    analysis: Analysis | None = None
    created: float = field(default_factory=time.monotonic)
    touched: float = field(default_factory=time.monotonic)


class JobNotFound(KeyError):
    pass


class JobStore:
    def __init__(self, ttl_seconds: float = 3600, max_jobs: int = 20):
        self.ttl = ttl_seconds
        self.max_jobs = max_jobs
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def _expire(self) -> None:
        now = time.monotonic()
        for jid in [j for j, job in self._jobs.items() if now - job.touched > self.ttl]:
            del self._jobs[jid]
        while len(self._jobs) > self.max_jobs:
            oldest = min(self._jobs.values(), key=lambda j: j.touched)
            del self._jobs[oldest.id]

    def create(self, frames: dict[str, pd.DataFrame], filenames: dict[str, str], sample: bool = False) -> Job:
        with self._lock:
            job = Job(uuid.uuid4().hex, frames, filenames, sample)
            self._jobs[job.id] = job
            self._expire()
            return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            self._expire()
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            job.touched = time.monotonic()
            return job

    def __len__(self) -> int:
        return len(self._jobs)
