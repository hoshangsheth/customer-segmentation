"""Read an uploaded CSV, TSV or Excel file into a DataFrame of strings, with size limits."""

from __future__ import annotations

import csv
import io
from pathlib import PurePath

import pandas as pd

MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 100_000
EXCEL = {".xlsx", ".xlsm", ".xls"}
TEXT = {".csv", ".tsv", ".txt"}


class IngestError(ValueError):
    """The file cannot be used; the message is shown to the user."""


def read_table(data: bytes, filename: str) -> pd.DataFrame:
    if not data:
        raise IngestError(f"{filename} is empty.")
    if len(data) > MAX_BYTES:
        raise IngestError(f"{filename} is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    ext = PurePath(filename).suffix.lower()
    if ext in EXCEL:
        try:
            df = pd.read_excel(io.BytesIO(data), dtype=str)
        except Exception as e:
            raise IngestError(f"Could not read {filename} as an Excel file: {e}") from None
    elif ext in TEXT or not ext:
        df = _read_text(data, filename)
    else:
        raise IngestError(f"{filename}: use a CSV, TSV or Excel (.xlsx) file.")

    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty or len(df.columns) < 2:
        raise IngestError(f"{filename} has no usable rows or columns.")
    if len(df) > MAX_ROWS:
        raise IngestError(f"{filename} has {len(df):,} rows; the limit is {MAX_ROWS:,}.")
    if len(set(df.columns)) != len(df.columns):
        raise IngestError(f"{filename} has duplicate column names.")
    return df.reset_index(drop=True)


def _read_text(data: bytes, filename: str) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    header = text.lstrip().splitlines()[0] if text.strip() else ""
    names = next(csv.reader([header], delimiter=sep)) if (sep := _delimiter(header)) else [header]
    if len(names) != len(set(n.strip() for n in names)):
        raise IngestError(f"{filename} has duplicate column names.")
    try:
        return pd.read_csv(io.StringIO(text), sep=sep or ",", dtype=str, skipinitialspace=True)
    except Exception as e:
        raise IngestError(f"Could not read {filename} as a delimited text file: {e}") from None


def _delimiter(header: str) -> str | None:
    """The most frequent of comma, semicolon, tab and pipe in the header line, or None."""
    counts = {d: header.count(d) for d in (",", ";", "\t", "|")}
    best = max(counts, key=counts.get)
    return best if counts[best] else None


def preview(df: pd.DataFrame, rows: int = 5) -> list[dict[str, str]]:
    return df.head(rows).fillna("").astype(str).to_dict(orient="records")
