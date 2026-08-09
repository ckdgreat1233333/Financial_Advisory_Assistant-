"""Clause-based chunking for regulatory documents.

A regulatory document is expected to begin with a small metadata header:

    Circular No: RBI/2025-26/09
    Date: 01-Aug-2025
    Issued By: Department of Regulation
    Subject: Master Direction - Know Your Customer (KYC)
    Version: v1.0
    Category: circular

followed by numbered clauses ("1.", "1.1", "2.4", ...). Each clause becomes
one chunk tagged with the document metadata (traceability requirements:
regulation name, circular number, issue date, version status).
"""
import hashlib
import re

from models.regulatory import RegulatoryChunk

HEADER_FIELD_MAP = {
    "circular no": "circular_no",
    "date": "issue_date",
    "subject": "title",
    "version": "version",
    "category": "category",
}

# Clause starts: "1. Heading", "1.1 Heading", "2.4 Heading". Requires the
# following word to start with an uppercase letter (headings are capitalized
# in the corpus), so prose lines like "5 years" are never treated as clauses.
CLAUSE_REF_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[\.\)]?\s+[A-Z]")
CLAUSE_START_RE = re.compile(r"(?:\d+(?:\.\d+)+\.?|[1-9]\d*\.)\s+[A-Z]")
CLAUSE_SPLIT_RE = re.compile(r"(?m)^\s*(?=" + CLAUSE_START_RE.pattern + ")")


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


class RegulatoryChunker:

    def parse_metadata(self, text: str) -> dict:
        """Extract the leading 'Key: Value' header fields."""
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

    def parse_document(self, doc_id: str, file_path: str, text: str) -> list[RegulatoryChunk]:
        """Parse raw text into metadata-carrying, clause-level chunks."""
        metadata = self.parse_metadata(text)
        title = metadata.get("title") or doc_id.replace("_", " ").title()
        circular_no = metadata.get("circular_no", "")
        issue_date = metadata.get("issue_date", "")
        version = metadata.get("version", "v1.0")

        chunks: list[RegulatoryChunk] = []
        for clause_text in self._split_clauses(text):
            match = CLAUSE_REF_RE.match(clause_text)
            clause_ref = match.group(1) if match else ""
            text_clean = clause_text.strip()
            if not text_clean or not clause_ref:
                continue
            chunks.append(
                RegulatoryChunk(
                    chunk_id=f"{doc_id}-{clause_ref.replace('.', '_')}",
                    text=text_clean,
                    clause_ref=clause_ref,
                    document_id=doc_id,
                    title=title,
                    circular_no=circular_no,
                    issue_date=issue_date,
                    version=version,
                )
            )
        return chunks

    def _split_clauses(self, text: str) -> list[str]:
        parts = CLAUSE_SPLIT_RE.split(text)
        clauses: list[str] = []
        for part in parts:
            chunk = part.strip()
            if chunk and CLAUSE_REF_RE.match(chunk):
                clauses.append(chunk)
        return clauses
