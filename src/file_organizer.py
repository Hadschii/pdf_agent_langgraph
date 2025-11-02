import re
import shutil
from datetime import datetime
from pathlib import Path

from src.logger import logger
from src.state import State


def organization_node(state: State) -> dict:
    """Build a filename and move the original PDF into a category folder.

    Uses Document_Date extracted by `text_analysis_node` when available. Falls back to today.

    Args:
        state: Workflow state expected to contain `entities`, `classification`,
               `summary`, and `file_path`.

    Returns:
        A dict containing `moved_path` and `filename` of the relocated file.
    """
    # grab values from state
    entities = state.get("entities") or {}
    organisation = entities.get("Organization", "unknown").strip()
    doc_date_raw = entities.get("Document_Date", "").strip()
    file_path = state.get("file_path", "")

    # Try to parse the document date into yymmdd, fallback to today
    date_prefix = None
    if doc_date_raw:
        # Try several common date formats
        for fmt in [
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d.%m.%y",
            "%d/%m/%Y",
            "%Y.%m.%d",
            "%d %B %Y",
            "%B %d, %Y",
        ]:
            try:
                dt = datetime.strptime(doc_date_raw, fmt)
                date_prefix = dt.strftime("%y%m%d")
                break
            except Exception:
                continue

    # Fallback to today
    if not date_prefix:
        date_prefix = datetime.now().strftime("%y%m%d")

    from src.config_loader import PDFConfig

    config = PDFConfig()

    # Get the normalized category, falls back to "sonstiges"
    category = config.normalize_category(state.get("classification", ""))

    # Format the target directory using config templates
    dt = datetime.strptime(date_prefix, "%y%m%d")
    target_dir = Path(
        config.format_folder_for_category(
            category, year=dt.strftime("%Y"), company=organisation, date=dt
        )
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    summary = (state.get("summary") or "nosummary").strip()

    # Use config to format the filename, passing source_path to preserve extension
    new_name = config.format_filename_for_category(
        category,
        company=organisation,
        content_summary=summary,
        date=dt,
        source_path=file_path,  # Pass source_path to preserve extension
    )
    logger.log(f"Moving file '{file_path}' to '{target_dir / new_name}'", level="info")
    moved_path = move_rename_file(file_path, new_name, str(target_dir))

    return {"moved_path": str(moved_path), "filename": Path(moved_path).name}


def sanitize_filename(filename: str, max_length: int = 120) -> str:
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    # Remove or replace unsupported characters
    filename = re.sub(r'[\\/:*?"<>|]', "_", filename)
    # Optionally, remove other problematic unicode chars
    filename = filename.replace("\n", "").replace("\r", "")
    # Truncate if too long
    if len(filename) > max_length:
        path = Path(filename)
        stem = path.stem[: max_length - len(path.suffix)]
        filename = f"{stem}{path.suffix}"
    return filename.lower()


def move_rename_file(original_path: str, new_name: str, target_directory: str) -> str:
    """Move and rename a file safely.

    Args:
        original_path: Path to the source file
        new_name: Desired filename (will be sanitized)
        target_directory: Destination directory path

    Returns:
        str: Path to the moved file, or original path if move failed
    """
    src_path = Path(original_path)
    dst_dir = Path(target_directory)
    sanitized_name = sanitize_filename(new_name)

    # Ensure target directory exists
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_path = dst_dir / sanitized_name

    try:
        # Preferred: shutil.move handles cross-filesystem moves and preserves metadata
        shutil.move(str(src_path), str(dst_path))
        return str(dst_path)
    except Exception as e:
        # Fallback: try an atomic replace (works on same filesystem)
        try:
            src_path.replace(dst_path)
            return str(dst_path)
        except Exception as e2:
            logger.log(
                f"Failed to move/rename file from '{src_path}' to '{dst_path}': {e} / {e2}",
                level="error",
            )
            return str(src_path)
