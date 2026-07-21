class PDFReader:
    def read(self, file_path: str) -> str:
        try:
            import fitz
            pdf = fitz.open(file_path)
            text = ""
            for page in pdf:
                text += page.get_text()
            pdf.close()
            return text
        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) is required for PDF reading. Install with: pip install PyMuPDF"
            )