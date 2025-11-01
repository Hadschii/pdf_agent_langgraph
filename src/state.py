from typing import Any, Dict, TypedDict


class State(TypedDict):
    """State dictionary for PDF processing workflow."""

    pdf_path: str
    pdf_text: str
    classification: str
    entities: Dict[str, Any]
    summary: str
