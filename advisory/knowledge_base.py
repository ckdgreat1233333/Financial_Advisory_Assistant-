"""Version-controlled knowledge base.

Ingestion pipeline:
    corpus files -> hash -> parse header + clause chunks -> embed -> FAISS index
                     + chunk-metadata JSON sidecar

The store re-ingests (and rebuilds the index) only when a file's hash changes
or new files appear, so the index is always reproducible from the corpus.
"""
import hashlib
import json
import logging
import re
from pathlib import Path

from database.faiss_db import FAISSDatabase
from models.advisory import KBChunk, RetrievedChunk

logger = logging.getLogger("advisory_kb")

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

CLAUSE_REF_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[\.\)]?\s+[A-Z]")


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


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


class VersionedKnowledgeStore:

    def __init__(
        self,
        corpus_dir,
        index_path,
        meta_path,
        embedder=None,
    ):
        self.corpus_dir = Path(corpus_dir)
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)

        self.embedder = embedder
        self.database = FAISSDatabase()

        self.chunks: list[KBChunk] = []
        self._ready = False
        self.ingest()

    def _ensure_embedder(self):
        if self.embedder is None:
            from advisory.embedder import Embedder
            self.embedder = Embedder()
        return self.embedder

    # ── Ingestion ──────────────────────────────────────────────

    def ingest(self) -> None:
        try:
            docs = self._scan_corpus()
        except Exception as exc:
            logger.warning("Corpus scan failed: %s", exc)
            return

        manifest = self._load_manifest()
        need_rebuild = not self._has_manifest_match(manifest, docs)

        if not need_rebuild:
            try:
                self.chunks = [self._chunk_from_dict(c) for c in manifest.get("chunks", [])]
                self.database.load(str(self.index_path))
                self._ready = self.database.index is not None
                logger.info("Knowledge store loaded from cached index (%d chunks)", len(self.chunks))
                return
            except Exception as exc:
                logger.warning("Failed to load cached index: %s", exc)
                need_rebuild = True

        from advisory.chunker import parse_metadata, split_clauses

        self.chunks = []
        for doc_id, file_path, doc_hash in docs:
            text = self._read_document(file_path)
            if not text.strip():
                logger.warning("Empty or unreadable document: %s", file_path)
                continue
            metadata = parse_metadata(text)
            title = metadata.get("title") or doc_id.replace("_", " ").title()
            category = metadata.get("category", "")
            version = metadata.get("version", "v1.0")

            doc_chunks: list[KBChunk] = []
            for clause_text in split_clauses(text):
                match = CLAUSE_REF_RE.match(clause_text)
                clause_ref = match.group(1) if match else ""
                clean = clause_text.strip()
                if not clean or not clause_ref:
                    continue
                doc_chunks.append(
                    KBChunk(
                        chunk_id=f"{doc_id}-{clause_ref.replace('.', '_')}",
                        text=clean,
                        clause_ref=clause_ref,
                        document_id=doc_id,
                        title=title,
                        category=category,
                        version=version,
                    ))
            if not doc_chunks:
                logger.warning("No clauses parsed from document: %s", file_path)
                continue
            self.chunks.extend(doc_chunks)

        self._rebuild_index()
        self._write_manifest({d[0]: d[2] for d in docs})
        self._ready = self.database.index is not None
        logger.info("Knowledge store rebuilt: %d chunks from %d documents",
                    len(self.chunks), len(docs))

    def _scan_corpus(self) -> list[tuple[str, str, str]]:
        if not self.corpus_dir.exists():
            self.corpus_dir.mkdir(parents=True, exist_ok=True)
            return []
        docs = []
        for path in sorted(self.corpus_dir.iterdir()):
            if path.is_dir() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            docs.append((path.stem, str(path), file_hash(str(path))))
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

    # ── Manifest ───────────────────────────────────────────────

    def _load_manifest(self) -> dict:
        if not self.meta_path.exists():
            return {"documents": {}, "chunks": []}
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"documents": {}, "chunks": []}

    @staticmethod
    def _has_manifest_match(manifest: dict, docs: list[tuple[str, str, str]]) -> bool:
        registered = manifest.get("documents", {})
        if len(registered) != len(docs):
            return False
        for doc_id, _, doc_hash in docs:
            if registered.get(doc_id) != doc_hash:
                return False
        return True

    def _write_manifest(self, documents: dict) -> None:
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "documents": documents,
            "chunks": [self._chunk_to_dict(c) for c in self.chunks],
        }
        self.meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                  encoding="utf-8")

    # ── Index ──────────────────────────────────────────────────

    def _rebuild_index(self) -> None:
        if not self.chunks:
            self.database.index = None
            return
        embeddings = self._ensure_embedder().embed([c.text for c in self.chunks])
        self.database.build(embeddings)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.database.save(str(self.index_path))

    # ── Retrieval ──────────────────────────────────────────────

    def retrieve(self, query: str, k: int = 4) -> list[RetrievedChunk]:
        if not self._ready or self.database.index is None or not self.chunks:
            return []
        query_embedding = self._ensure_embedder().embed_query(query)
        distances, indices = self.database.search(query_embedding, k)
        results: list[RetrievedChunk] = []
        for i in range(len(indices[0])):
            idx = int(indices[0][i])
            if idx < 0 or idx >= len(self.chunks):
                continue
            distance = float(distances[0][i])
            similarity = max(0.0, min(1.0, 1.0 - (distance * distance) / 2.0))
            results.append(RetrievedChunk(chunk=self.chunks[idx], similarity=similarity))
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results

    # ── Serialization helpers ──────────────────────────────────

    @staticmethod
    def _chunk_to_dict(c: KBChunk) -> dict:
        return {
            "chunk_id": c.chunk_id, "text": c.text, "clause_ref": c.clause_ref,
            "document_id": c.document_id, "title": c.title,
            "category": c.category, "version": c.version,
        }

    @staticmethod
    def _chunk_from_dict(d: dict) -> KBChunk:
        return KBChunk(
            chunk_id=d.get("chunk_id", ""), text=d.get("text", ""),
            clause_ref=d.get("clause_ref", ""), document_id=d.get("document_id", ""),
            title=d.get("title", ""), category=d.get("category", ""),
            version=d.get("version", "v1.0"),
        )
