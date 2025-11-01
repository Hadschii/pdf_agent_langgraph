from datetime import datetime
from pathlib import Path

import yaml


def load_config():
    """Backward-compatible helper: returns the raw parsed config dict.

    This looks for common config locations (project-level) and loads the first
    one found. Prefer using the PDFConfig class below for richer behaviour.
    """
    cfg = PDFConfig()
    return cfg.data


class ConfigError(Exception):
    pass


class PDFConfig:
    """Wrapper around a YAML config file that provides convenient accessors.

    Behaviour:
    - If config_path is None, searches common locations relative to the repo root.
    - Resolves relative folder paths against the project root.
    - Provides helpers to format category-specific folder and filename templates.
    """

    def __init__(self, config_path: str | None = None):
        # project root (assume src is inside repo root)
        self.project_root = Path(__file__).parent.parent.resolve()

        # simple behaviour: config is expected in ./config/config.yaml relative to project root
        if config_path:
            path = Path(config_path)
            self.config_path = (
                (self.project_root / config_path).resolve()
                if not path.is_absolute()
                else path
            )
        else:
            self.config_path = self.project_root / "config" / "config.yaml"

        self.data = self._load_config()
        self._validate()

    # NOTE: simplified: no search across multiple locations. We expect the config
    # to live at ./config/config.yaml relative to the project root unless a
    # specific path is provided to the constructor.

    def _load_config(self):
        """Read and parse the YAML config file.

        Returns:
            The parsed config as a dict.

        Raises:
            ConfigError: if the file cannot be read or parsed.
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise ConfigError(f"Config file not found: {self.config_path}")
        except Exception as e:
            raise ConfigError(f"Failed to read config file {self.config_path}: {e}")

    def _validate(self):
        """Perform basic validation of required config keys and structures.

        Raises:
            ConfigError: if required keys are missing or if expected structures
                (like category_list or category_paths) have the wrong type.
        """
        # minimal validation; keep flexible but warn on missing common keys
        required = ["input_folder", "output_folder", "report_folder"]
        missing = [k for k in required if k not in self.data]
        if missing:
            raise ConfigError(f"Missing required config keys: {', '.join(missing)}")

        # ensure category structures exist
        if "category_list" in self.data and not isinstance(
            self.data["category_list"], list
        ):
            raise ConfigError("'category_list' must be a list")

        if "category_paths" in self.data and not isinstance(
            self.data["category_paths"], dict
        ):
            raise ConfigError("'category_paths' must be a mapping/dict")

    # basic properties
    @property
    def llm_model(self) -> str:
        return self.data.get("llm_model", "gpt-5-nano")

    @property
    def llm_temperature(self) -> float:
        return float(self.data.get("llm_temperature", 0))

    @property
    def input_folder(self) -> str:
        return self._resolve_path(self.data["input_folder"])
    

    @property
    def input_folder(self) -> str:
        return self._resolve_path(self.data["input_folder"])

    @property
    def output_folder(self) -> str:
        return self._resolve_path(self.data["output_folder"])

    @property
    def report_folder(self) -> str:
        return self._resolve_path(self.data["report_folder"])

    @property
    def default_naming(self) -> str:
        return self.data.get(
            "default_naming", "{date}_{category}_{company}_{content_summary}.pdf"
        )

    @property
    def date_format(self) -> str:
        return self.data.get("date_format", "%y%m%d")

    @property
    def language(self) -> str:
        return self.data.get("language", "de")

    @property
    def label_threshold(self) -> float:
        return float(self.data.get("label_threshold", 0.8))

    @property
    def category_list(self) -> list:
        return self.data.get("category_list", [])

    @property
    def labels(self) -> list:
        return self.data.get("labels", [])

    @property
    def category_paths(self) -> dict:
        return self.data.get("category_paths", {})

    # helpers
    def _resolve_path(self, path_str: str) -> str:
        """Resolve a path string to an absolute path, handling ~ and env vars."""
        if not path_str:
            return path_str
        
        # Create Path object and resolve ~ and env vars
        path = Path(path_str).expanduser()
        
        # If relative, resolve against project root
        if not path.is_absolute():
            path = self.project_root / path
            
        return str(path.resolve())

    def normalize_category(self, category: str) -> str:
        """Normalize a category string to a known config key.

        Returns the configured category key (lowercased) if it exists; falls
        back to `'sonstiges'` when no match is found.
        """
        if not category:
            return "sonstiges"
        # config uses lowercase keys; map case-insensitively
        key = category.strip().lower()
        if key in self.category_paths:
            return key
        # try mapping a few common German capitalizations
        mapping = {k.lower(): k for k in self.category_paths.keys()}
        return mapping.get(key, "sonstiges")

    def get_category_config(self, category: str) -> dict:
        """Return the raw configuration mapping for a normalized category.

        Args:
            category: Category name (any capitalization).

        Returns:
            The category config dict or an empty dict when missing.
        """
        key = self.normalize_category(category)
        return self.category_paths.get(key, {})

    def get_naming_for_category(self, category: str, label: str | None = None) -> str:
        """Return the naming template for the category, applying label overrides.

        If a label override exists for the provided label it is used; otherwise
        falls back to the category's naming or the global default naming.
        """
        cfg = self.get_category_config(category)
        # check label overrides
        if label and "label_overrides" in cfg:
            overrides = cfg.get("label_overrides", {})
            if label in overrides and "naming" in overrides[label]:
                return overrides[label]["naming"]
        return cfg.get("naming", self.default_naming)

    def format_folder_for_category(
        self,
        category: str,
        *,
        year: str | None = None,
        company: str | None = None,
        date: datetime | None = None,
        label: str | None = None,
    ) -> str:
        cfg = self.get_category_config(category)
        folder_tpl = None
        # label overrides may also change folder
        if label and "label_overrides" in cfg:
            ld = cfg.get("label_overrides", {}).get(label, {})
            folder_tpl = ld.get("folder")

        if not folder_tpl:
            folder_tpl = cfg.get("folder")

        if not folder_tpl:
            # fallback to output folder
            return self.output_folder

        # prepare date/year
        if date is None:
            date = datetime.now()
        if year is None:
            year = date.strftime("%Y")

        variables = {
            "year": year,
            "company": company or "unknown",
            "date": date.strftime(self.date_format),
            "content_summary": "",
        }

        try:
            folder = folder_tpl.format(**variables)
        except Exception:
            # best-effort: return as-is
            folder = folder_tpl

        # Join with output_folder as the base path, then resolve to absolute
        folder_path = Path(self.output_folder) / folder
        return str(folder_path.resolve())

    def format_filename_for_category(
        self,
        category: str,
        *,
        company: str | None = None,
        content_summary: str | None = None,
        date: datetime | None = None,
        label: str | None = None,
        source_path: str | None = None,
    ) -> str:
        # Get original extension if available, default to no extension
        ext = Path(source_path).suffix if source_path else ""
        # Remove .pdf from template if present (it'll be in the extension if needed)
        naming = self.get_naming_for_category(category, label=label)
        naming = Path(naming).stem  # remove extension if present
        if date is None:
            date = datetime.now()

        variables = {
            "date": date.strftime(self.date_format),
            "category": category,
            "company": company or "unknown",
            "content_summary": (content_summary or "").replace(" ", "_"),
        }
        try:
            return naming.format(**variables) + ext
        except Exception:
            # fallback to a safe filename
            safe = f"{variables['date']}_{variables['category']}_{variables['company']}_{variables['content_summary']}{ext}"
            return safe

    def __repr__(self) -> str:
        return f"PDFConfig(path={self.config_path!r})"
