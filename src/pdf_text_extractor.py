from pathlib import Path
from typing import Dict, Tuple

import pytesseract
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.parsers import TesseractBlobParser
from pdf2image import convert_from_path

from src.logger import logger
from src.state import State


def pdf_extraction_node(state: State) -> Dict[str, str]:
    """Node: extract text from the provided PDF path and return it in the state.

    Args:
        state: Workflow state containing at least the key `file_path`.

    Returns:
        A dict containing the extracted PDF text under the key `file_text`.
    """

    pdf_path = state.get("file_path", "")
    extracted_text, method = extract_text_from_pdf(pdf_path)
    return {"file_text": extracted_text}


def extract_text_from_pdf(file_path: str) -> Tuple[str, str]:
    """Extract text from a PDF using multiple strategies and return (text, method).

    Strategy:
      1. Try native text extraction with PyPDFLoader
      2. If empty, try PyPDFLoader with TesseractBlobParser()
      3. If still empty, use pytesseract on images from pdf2image

    Args:
        file_path: Path to PDF file.

    Returns:
        Tuple[text, method] where method is one of "Native", "ocr-tesseract", or
        "pytesseract via image" depending on the approach that succeeded.
    """

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extracted_text = ""
    extraction_method = ""

    # First attempt: use PyPDFLoader
    try:
        loader = PyPDFLoader(str(path))
        pages = loader.load_and_split()
        extracted_text = "\n".join(page.page_content for page in pages).strip()
        if extracted_text:
            extraction_method = "Native"
            return extracted_text, extraction_method
    except Exception as e:
        logger.log(f"PyPDFLoader failed: {e}", level="error")

    # Second attempt: TesseractBlobParser via PyPDFLoader
    try:
        parser = TesseractBlobParser(langs="deu+eng")
        loader = PyPDFLoader(str(path), extract_images=True, images_parser=parser)
        pages = list(loader.lazy_load())
        extracted_text = "\n".join(
            getattr(p, "page_content", "") for p in pages
        ).strip()
        if extracted_text:
            extraction_method = "ocr-tesseract"
            return extracted_text, extraction_method
    except Exception as e:
        logger.log(f"TesseractBlobParser failed: {e}", level="error")

    # Fallback: convert pdf to images and scan with OCR
    if not extracted_text:
        try:
            images = convert_from_path(file_path)
            for img in images:
                extracted_text += pytesseract.image_to_string(img, lang="deu+eng")
            if extracted_text:
                extraction_method = "pytesseract via image"
                return extracted_text, extraction_method
        except Exception as e:
            logger.log(f"UnstructuredPDFLoader failed: {e}", level="error")

    return extracted_text, extraction_method
