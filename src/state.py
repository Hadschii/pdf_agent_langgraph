from typing import Any, Dict, TypedDict


class State(TypedDict):
    """State dictionary for PDF processing workflow."""

    file_path: str
    file_text: str
    classification: str
    entities: Dict[str, Any]
    summary: str
