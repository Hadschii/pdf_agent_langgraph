import pytest

from main import type_detection_node


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("/some/path/doc.pdf", "pdf_extraction_node"),
        ("/some/path/image.png", "img_extraction_node"),
        ("/some/path/photo.JPG", "img_extraction_node"),
        ("/some/path/scan.JpEg", "img_extraction_node"),
        ("", "pdf_extraction_node"),
    ],
)
def test_type_detection_various(filename, expected):
    # type_detection_node expects a mapping with get(), a plain dict is fine
    state = {"file_path": filename}
    result = type_detection_node(state)
    assert result == expected
