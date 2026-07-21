from document_processing.document_processor import DocumentProcessor


class DocumentAgent:

    def __init__(self):
        self.processor = DocumentProcessor()

    def process(
        self,
        file_path: str,
        document_type: str,
    ):
        return self.processor.process(
            file_path=file_path,
            document_type=document_type,
        )