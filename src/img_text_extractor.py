from pathlib import Path
from typing import Any, Dict, Tuple

import pytesseract
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.parsers import TesseractBlobParser
from pdf2image import convert_from_path
from PIL import Image

from src.logger import logger
from src.state import State

def img_extraction_node(state: State) -> Dict[str, str]:
    """Node: extract text from the provided Image path and return it in the state.

    Args:
        state: Workflow state containing at least the key `file_path`.

    Returns:
        A dict containing the extracted Image text under the key `file_text`.
    """
    img_path = state.get("file_path", "")
    extracted_text, method = extract_text_from_image(img_path)
    return {"file_text": extracted_text}


def extract_text_from_image(
    file_path: str, ocr_languages: str = "deu+eng"
) -> Tuple[str, str]:
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
            logger.log(
                f"Extracted text from image {file_path} using pytesseract; {len(extracted_text)} chars",
                level="info",
            )
        else:
            logger.log(
                f"No text found in image {file_path} using pytesseract.",
                level="warning",
            )
        return extracted_text, extraction_method
    except Exception as e:
        logger.log(f"Failed to OCR image {file_path}: {e}", level="error")
        return "", ""