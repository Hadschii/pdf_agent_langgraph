from pathlib import Path
from typing import Tuple, Dict, Any

import pytesseract
from PIL import Image
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.parsers import TesseractBlobParser
from pdf2image import convert_from_path
from src.state import State

from src.logger import logger


def text_extraction_node(state: State) -> Dict[str, str]:
    """Node: extract text from the provided PDF path and return it in the state.

    Args:
        state: Workflow state containing at least the key `pdf_path`.

    Returns:
        A dict containing the extracted PDF text under the key `pdf_text`.
    """

    pdf_path = state.get("pdf_path", "")
    extracted_text, method = extract_text_from_file(pdf_path)
    return {"pdf_text": extracted_text}


def extract_text_from_file(file_path: str) -> Tuple[str, str]:
    """Convenience router: choose image OCR or PDF extraction based on extension.

    Args:
        file_path: Path to a PDF or image file.

    Returns:
        Tuple[text, method] where `method` describes how the text was obtained.
    """
    path = Path(file_path)
    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    if path.suffix.lower() in image_exts:
        logger.log(f"Image file support is experimental. Extracting text from image file: {file_path}", level="warning")
        return extract_text_from_image(file_path)
    return extract_text_from_pdf(file_path)


def extract_text_from_image(file_path: str, ocr_languages: str = "deu+eng") -> Tuple[str, str]:
    """Run pytesseract on an image file and return (text, method).

    Args:
        file_path: Path to the image file to OCR.
        ocr_languages: Tesseract language codes (e.g. "deu+eng").

    Returns:
        Tuple[text, method]
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        img = Image.open(path)
        extracted_text = pytesseract.image_to_string(img, lang=ocr_languages)
        extraction_method = "image-pytesseract"
        if extracted_text:
            logger.log(f"Extracted text from image {file_path} using pytesseract; {len(extracted_text)} chars", level="info")
        else:
            logger.log(f"No text found in image {file_path} using pytesseract.", level="warning")
        return extracted_text, extraction_method
    except Exception as e:
        logger.log(f"Failed to OCR image {file_path}: {e}", level="error")
        return "", ""


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
