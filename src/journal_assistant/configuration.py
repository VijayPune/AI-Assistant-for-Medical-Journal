"""Load and validate application and journal configuration using the stdlib."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_CONFIG_PATH = PROJECT_ROOT / "config" / "app.toml"
JOURNAL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ConfigurationError(ValueError):
    """Raised when a TOML configuration is missing or invalid."""


@dataclass(frozen=True)
class JournalConfig:
    journal_id: str
    display_name: str
    homepage_url: str
    issues_url: str
    article_index_url: str
    corpus_title: str
    issue_id: str
    publication_date: date
    volume: int
    issue_number: int
    access_review_status: str
    full_text_permission: str
    config_path: Path
    metadata_file: Path
    raw_files_directory: Path


def _read_toml(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"Invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"Configuration must contain a TOML table: {path}")
    return data


def _require_text(data: dict, key: str, *, source: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"'{key}' must be a non-empty string in {source}")
    return value.strip()


def _require_https_url(data: dict, key: str, *, source: str) -> str:
    value = _require_text(data, key, source=source)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ConfigurationError(f"'{key}' must be an absolute HTTPS URL in {source}")
    return value


def resolve_journal_config_path(config_path: str | Path | None = None) -> Path:
    """Resolve an explicit path, environment override, or configured default."""
    selected = config_path or os.environ.get("JOURNAL_ASSISTANT_CONFIG")
    if selected is None:
        app_data = _read_toml(APP_CONFIG_PATH)
        application = app_data.get("application")
        if not isinstance(application, dict):
            raise ConfigurationError("'application' table is required in config/app.toml")
        selected = _require_text(
            application, "default_journal_config", source=str(APP_CONFIG_PATH)
        )

    path = Path(selected).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_journal_config(config_path: str | Path | None = None) -> JournalConfig:
    """Read a journal TOML file and validate its Step 1 fields."""
    path = resolve_journal_config_path(config_path)
    data = _read_toml(path)
    source = str(path)

    journal_id = _require_text(data, "journal_id", source=source)
    if not JOURNAL_ID_PATTERN.fullmatch(journal_id):
        raise ConfigurationError(
            "'journal_id' must use lowercase letters, digits, underscores, or hyphens"
        )

    initial_corpus = data.get("initial_corpus")
    access = data.get("access")
    corpus = data.get("corpus", {})
    if not isinstance(initial_corpus, dict):
        raise ConfigurationError(f"'initial_corpus' table is required in {source}")
    if not isinstance(access, dict):
        raise ConfigurationError(f"'access' table is required in {source}")
    if not isinstance(corpus, dict):
        raise ConfigurationError(f"'corpus' must be a TOML table in {source}")

    pub_date = initial_corpus.get("publication_date")
    if isinstance(pub_date, str):
        try:
            pub_date = date.fromisoformat(pub_date)
        except ValueError as exc:
            raise ConfigurationError(
                f"'publication_date' must use YYYY-MM-DD format in {source}"
            ) from exc
    if not isinstance(pub_date, date):
        raise ConfigurationError(f"'publication_date' is required in {source}")

    volume = initial_corpus.get("volume")
    issue_number = initial_corpus.get("issue_number")
    if not isinstance(volume, int) or volume < 1:
        raise ConfigurationError(f"'volume' must be a positive integer in {source}")
    if not isinstance(issue_number, int) or issue_number < 1:
        raise ConfigurationError(f"'issue_number' must be a positive integer in {source}")

    metadata_file = Path(str(corpus.get("metadata_file", "data/metadata/article_metadata.csv")))
    raw_files_directory = Path(str(corpus.get("raw_files_directory", "data/raw")))
    if not metadata_file.is_absolute():
        metadata_file = PROJECT_ROOT / metadata_file
    if not raw_files_directory.is_absolute():
        raw_files_directory = PROJECT_ROOT / raw_files_directory

    return JournalConfig(
        journal_id=journal_id,
        display_name=_require_text(data, "display_name", source=source),
        homepage_url=_require_https_url(data, "homepage_url", source=source),
        issues_url=_require_https_url(data, "issues_url", source=source),
        article_index_url=_require_https_url(data, "article_index_url", source=source),
        corpus_title=_require_text(initial_corpus, "title", source=source),
        issue_id=_require_text(initial_corpus, "issue_id", source=source),
        publication_date=pub_date,
        volume=volume,
        issue_number=issue_number,
        access_review_status=_require_text(access, "review_status", source=source),
        full_text_permission=_require_text(access, "full_text_permission", source=source),
        config_path=path,
        metadata_file=metadata_file.resolve(),
        raw_files_directory=raw_files_directory.resolve(),
    )
