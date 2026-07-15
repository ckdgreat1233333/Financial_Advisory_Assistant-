import fitz
class PDFReader:
    def read(self, file_path: str) -> str:
        pdf = fitz.open(file_path)
        text = ""
        for page in pdf:
            text += page.get_text()
        pdf.close()
        return text