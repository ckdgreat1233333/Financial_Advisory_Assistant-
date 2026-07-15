from dataclasses import dataclass, field
from datetime import datetime
import uuid

from utils.enums import (
    DocumentType,
    ValidationStatus,
    ValidationError,
)


@dataclass(kw_only=True)
class Document:
    document_name: str
    document_type: DocumentType
    file_path: str
    extracted_text: str
    ocr_confidence: float | None = None
    validation_status: ValidationStatus
    validation_error: ValidationError
    extraction_method: str
    metadata: dict = field(default_factory=dict)
    processed_at: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))