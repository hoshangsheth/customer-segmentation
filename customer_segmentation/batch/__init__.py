"""
Batch analysis of an uploaded customer file: map its columns to what the models need, validate and
clean the rows, then segment and score every customer.

Pipeline: ingest (read CSV or Excel) -> prepare (map, merge, validate) -> analyze (segment, score,
explain, summarise). Uploaded data lives only in memory (jobs.JobStore) and expires.
"""
