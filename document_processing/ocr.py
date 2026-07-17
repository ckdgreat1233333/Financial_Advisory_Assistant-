from pathlib import Path
from typing import Optional

import cv2
import easyocr
import fitz
import numpy as np
from pdf2image import convert_from_path


class OCRProcessor:
    """
    Enterprise OCR Processor.

    Features
    --------
    • Searchable PDF detection
    • Automatic OCR fallback
    • Image OCR
    • Confidence score
    • Multi-page support
    """

    def __init__(self):

        self.reader = easyocr.Reader(
            ["en"],
            gpu=False
        )

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def extract_text(
        self,
        file_path: str,
    ) -> tuple[str, float]:

        path = Path(file_path)

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._process_pdf(file_path)

        if suffix in [".png", ".jpg", ".jpeg"]:

            return self._process_image(file_path)

        raise ValueError(
            f"Unsupported file format: {suffix}"
        )

    # -----------------------------------------------------
    # PDF Processing
    # -----------------------------------------------------

    def _process_pdf(
        self,
        pdf_path: str,
    ) -> tuple[str, float]:

        document = fitz.open(pdf_path)

        extracted_text = ""

        for page in document:

            extracted_text += page.get_text()

        document.close()

        # Searchable PDF

        if extracted_text.strip():

            return extracted_text, 1.0

        # Scanned PDF

        pages = convert_from_path(pdf_path)

        full_text = []

        confidences = []

        for page in pages:

            image = np.array(page)

            text, confidence = self._ocr(image)

            full_text.append(text)

            confidences.append(confidence)

        average = (
            sum(confidences) / len(confidences)
            if confidences
            else 0
        )

        return "\n".join(full_text), average

    # -----------------------------------------------------
    # Image Processing
    # -----------------------------------------------------

    def _process_image(
        self,
        image_path: str,
    ) -> tuple[str, float]:

        image = cv2.imread(image_path)

        return self._ocr(image)

    # -----------------------------------------------------
    # OCR Engine
    # -----------------------------------------------------

    def _ocr(
        self,
        image,
    ) -> tuple[str, float]:

        results = self.reader.readtext(
            image,
            detail=1,
            paragraph=True,
        )

        text = []

        confidence = []

        for _, value, score in results:

            text.append(value)

            confidence.append(score)

        final_text = "\n".join(text)

        average = (
            sum(confidence) / len(confidence)
            if confidence
            else 0
        )

        return final_text, average

    # -----------------------------------------------------
    # Validation Helper
    # -----------------------------------------------------

    @staticmethod
    def is_confident(
        score: float,
        threshold: float = 0.75,
    ) -> bool:

        return score >= threshold