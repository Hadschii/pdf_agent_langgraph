import csv
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from src.config_loader import PDFConfig


class Logger:
    """A small wrapper around Python's logging that also writes simple CSV reports.

    Use the module-level `logger` instance instead of constructing Logger instances
    across modules. The logger uses paths from PDFConfig by default.
    """

    def __init__(self, config: Optional[PDFConfig] = None, name: str = "pdf_agent"):
        self.config = config or PDFConfig()
        # Use the configured report folder for both logs and reports
        report_dir = self.config.report_folder
        os.makedirs(report_dir, exist_ok=True)

        self.reports_dir = report_dir
        self.log_path = os.path.join(report_dir, "agent.log")

        self._logger = logging.getLogger(name)
        # Prevent adding multiple handlers if this module is imported multiple times
        if not self._logger.handlers:
            fh = logging.FileHandler(self.log_path, encoding="utf-8")
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            fh.setFormatter(formatter)
            self._logger.setLevel(logging.INFO)
            self._logger.addHandler(fh)

    def log(self, message: str, level: str = "info") -> None:
        if level == "error":
            self._logger.error(message)
        elif level == "warning":
            self._logger.warning(message)
        else:
            self._logger.info(message)

    def create_report(self, records: List[Dict[str, str]]) -> str:
        """Write a CSV report into the reports dir and return its path.

        records: list of dicts with keys: original, new, category, timestamp, status, error
        """
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.reports_dir, f"report_{now}.csv")
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "original",
                    "new",
                    "category",
                    "timestamp",
                    "status",
                    "error",
                ],
            )
            writer.writeheader()
            for rec in records:
                writer.writerow(rec)
        # Log via the configured logger
        self.log(f"Report created: {report_path}")
        return report_path


# Module-level singleton logger. Import this in other modules with:
#   from src.logger import logger
logger = Logger()

__all__ = ["Logger", "logger"]
