"""Clause-based chunking for knowledge-base documents.

A corpus document begins with a small metadata header:

    Subject: Smart Fixed Deposit
    Category: deposit
    Version: v1.0

followed by numbered clauses ("1.", "1.1", "2.4", ...). Each clause becomes
one chunk tagged with document metadata, enabling clause-level citations.
"""
import re

HEADER_FIELD_MAP = {
    "subject": "title",
    "category": "category",
    "version": "version",
}

CLAUSE_REF_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[\.\)]?\s+[A-Z]")
CLAUSE_START_RE = re.compile(r"(?:\d+(?:\.\d+)+\.?|[1-9]\d*\.)\s+[A-Z]")
CLAUSE_SPLIT_RE = re.compile(r"(?m)^\s*(?=" + CLAUSE_START_RE.pattern + ")")


def parse_metadata(text: str) -> dict:
    metadata: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = re.match(r"^\s*([A-Za-z][A-Za-z /()&.\-']{2,60}?)\s*:\s*(.*)$", line)
        if not m:
            break
        key = m.group(1).strip().lower()
        value = m.group(2).strip()
        if key in HEADER_FIELD_MAP:
            metadata[HEADER_FIELD_MAP[key]] = value
    return metadata


def split_clauses(text: str) -> list[str]:
    parts = CLAUSE_SPLIT_RE.split(text)
    clauses: list[str] = []
    for part in parts:
        chunk = part.strip()
        if chunk and CLAUSE_REF_RE.match(chunk):
            clauses.append(chunk)
    return clauses
