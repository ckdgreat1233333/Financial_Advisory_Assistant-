"""Version-controlled knowledge store for regulatory documents.

Ingestion pipeline:
    corpus files -> hash -> parse header + clause chunks -> embed -> FAISS index
                     + chunk-metadata JSON sidecar + SQLite registry

The store re-ingests (and rebuilds the index) only when a file's hash
changes or new files appear. This gives the "version-controlled knowledge
store" property: the index is always reproducible from the approved corpus.
"""
import json
import logging
import os
from pathlib import Path

from database.faiss_db import FAISSDatabase
from models.regulatory import RegulatoryDocument, RegulatoryChunk, RetrievedChunk
from regulatory.chunker import RegulatoryChunker, file_hash
from regulatory.embedder import RegulatoryEmbedder

logger = logging.getLogger("claims_assistant")

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def _read_pdf(path: Path) -> str:
    try:
        import fitz
    except ImportError:
        logger.warning("PyMuPDF (fitz) not installed; skipping %s", path.name)
        return ""
    text_parts = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


class RegulatoryKnowledgeStore:

    def __init__(
        self,
        corpus_dir: str | None = None,
        index_path: str | None = None,
        meta_path: str | None = None,
        embedder=None,
        chunker=None,
        register: bool = True,
    ):
        base = Path(__file__).resolve().parent.parent
        self.corpus_dir = Path(corpus_dir or (base / "data" / "regulatory"))
        self.index_path = Path(index_path or (base / "data" / "indexes" / "regulatory_index.bin"))
        self.meta_path = Path(meta_path or (base / "data" / "indexes" / "regulatory_chunks.json"))

        self.embedder = embedder or RegulatoryEmbedder()
        self.chunker = chunker or RegulatoryChunker()
        self.database = FAISSDatabase()
        self.register = register

        self.chunks: list[RegulatoryChunk] = []
        self._ready = False
        self.ingest()

    # ── Ingestion ──────────────────────────────────────────────

    def ingest(self) -> None:
        try:
            docs = self._scan_corpus()
        except Exception as exc:
            logger.warning("Regulatory corpus scan failed: %s", exc)
            return

        manifest = self._load_manifest()
        need_rebuild = not self._has_manifest_match(manifest, docs)

        if not need_rebuild:
            try:
                self.chunks = [self._chunk_from_dict(c) for c in manifest.get("chunks", [])]
                self.database.load(str(self.index_path))
                self._ready = self.database.index is not None
                logger.info("Regulatory store loaded from cached index (%d chunks)", len(self.chunks))
                return
            except Exception as exc:
                logger.warning("Failed to load cached regulatory index: %s", exc)
                need_rebuild = True

        self.chunks = []
        for doc in docs:
            text = self._read_document(doc.file_path)
            if not text.strip():
                logger.warning("Empty or unreadable regulatory document: %s", doc.file_path)
                continue
            metadata = self.chunker.parse_metadata(text)
            doc.title = metadata.get("title") or doc.title
            doc.circular_no = metadata.get("circular_no", "")
            doc.issue_date = metadata.get("issue_date", "")
            doc.version = metadata.get("version", doc.version)
            doc.category = metadata.get("category", doc.category)
            doc_chunks = self.chunker.parse_document(doc.doc_id, doc.file_path, text)
            if not doc_chunks:
                logger.warning("No clauses parsed from regulatory document: %s", doc.file_path)
                continue
            self.chunks.extend(doc_chunks)
            self._upsert_registry(doc)

        self._rebuild_index()
        self._write_manifest(docs)
        self._ready = self.database.index is not None
        logger.info("Regulatory store rebuilt: %d chunks from %d documents", len(self.chunks), len(docs))

    def _scan_corpus(self) -> list[RegulatoryDocument]:
        if not self.corpus_dir.exists():
            self.corpus_dir.mkdir(parents=True, exist_ok=True)
            return []
        docs = []
        for path in sorted(self.corpus_dir.iterdir()):
            if path.is_dir() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            doc_id = path.stem
            docs.append(
                RegulatoryDocument(
                    doc_id=doc_id,
                    title=doc_id.replace("_", " ").title(),
                    circular_no="",
                    issue_date="",
                    version="v1.0",
                    file_path=str(path),
                    file_hash=file_hash(str(path)),
                    category="circular",
                )
            )
        return docs

    def _read_document(self, path: str) -> str:
        path_obj = Path(path)
        if path_obj.suffix.lower() == ".pdf":
            return _read_pdf(path_obj)
        try:
            return path_obj.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            try:
                return path_obj.read_text(encoding="latin-1")
            except OSError:
                return ""

    def _load_manifest(self) -> dict:
        if not self.meta_path.exists():
            return {"documents": {}, "chunks": []}
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"documents": {}, "chunks": []}

    def _has_manifest_match(self, manifest: dict, docs: list[RegulatoryDocument]) -> bool:
        registered = manifest.get("documents", {})
        if len(registered) != len(docs):
            return False
        for doc in docs:
            if registered.get(doc.doc_id) != doc.file_hash:
                return False
        return True

    def _write_manifest(self, docs: list[RegulatoryDocument]) -> None:
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "documents": {doc.doc_id: doc.file_hash for doc in docs},
            "chunks": [self._chunk_to_dict(c) for c in self.chunks],
        }
        self.meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    def _rebuild_index(self) -> None:
        if not self.chunks:
            self.database.index = None
            return
        embeddings = self.embedder.embed([c.text for c in self.chunks])
        self.database.build(embeddings)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.database.save(str(self.index_path))

    def _upsert_registry(self, doc: RegulatoryDocument) -> None:
        if not self.register:
            return
        try:
            from database import db as database_db
            database_db.upsert_regulatory_doc(
                doc_id=doc.doc_id,
                title=doc.title,
                circular_no=doc.circular_no,
                issue_date=doc.issue_date,
                version=doc.version,
                category=doc.category,
                file_path=doc.file_path,
                file_hash=doc.file_hash,
            )
        except Exception as exc:
            logger.warning("Could not update regulatory registry for %s: %s", doc.doc_id, exc)

    # ── Retrieval ──────────────────────────────────────────────

    def retrieve(self, query: str, k: int = 4) -> list[RetrievedChunk]:
        if not self._ready or self.database.index is None or not self.chunks:
            return []
        query_embedding = self.embedder.embed_query(query)
        distances, indices = self.database.search(query_embedding, k)
        results: list[RetrievedChunk] = []
        for i in range(len(indices[0])):
            idx = int(indices[0][i])
            if idx < 0 or idx >= len(self.chunks):
                continue
            # Embeddings are L2-normalized, so cosine = 1 - d^2 / 2.
            distance = float(distances[0][i])
            similarity = max(0.0, min(1.0, 1.0 - (distance * distance) / 2.0))
            results.append(RetrievedChunk(chunk=self.chunks[idx], similarity=similarity))
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results

    # ── Serialization helpers ──────────────────────────────────

    @staticmethod
    def _chunk_to_dict(c: RegulatoryChunk) -> dict:
        return {
            "chunk_id": c.chunk_id,
            "text": c.text,
            "clause_ref": c.clause_ref,
            "document_id": c.document_id,
            "title": c.title,
            "circular_no": c.circular_no,
            "issue_date": c.issue_date,
            "version": c.version,
        }

    @staticmethod
    def _chunk_from_dict(d: dict) -> RegulatoryChunk:
        return RegulatoryChunk(
            chunk_id=d.get("chunk_id", ""),
            text=d.get("text", ""),
            clause_ref=d.get("clause_ref", ""),
            document_id=d.get("document_id", ""),
            title=d.get("title", ""),
            circular_no=d.get("circular_no", ""),
            issue_date=d.get("issue_date", ""),
            version=d.get("version", ""),
        )
