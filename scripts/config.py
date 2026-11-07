"""
Configuration Module for Resume Job Tracker.

Single Source of Truth for filesystem paths, constants, default settings,
and exit codes. All paths are resolved relative to the repository root.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional


class Config:
    # Repository Root
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

    # Core Directories
    DB_DIR: Path = PROJECT_ROOT / "db"
    SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
    MASTER_DIR: Path = PROJECT_ROOT / "master"
    VARIANTS_DIR: Path = PROJECT_ROOT / "variants"
    TEMPLATES_DIR: Path = PROJECT_ROOT / "cover_letters"
    GENERATED_DIR: Path = PROJECT_ROOT / "generated"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"
    TESTS_DIR: Path = PROJECT_ROOT / "tests"

    # Core Files
    DB_PATH: Path = DB_DIR / "positions.db"
    SCHEMA_SQL_PATH: Path = DB_DIR / "schema.sql"
    SCHEMA_MD_PATH: Path = DB_DIR / "schema.md"
    DASHBOARD_HTML_PATH: Path = PROJECT_ROOT / "dashboard.html"
    PIPELINE_MD_PATH: Path = PROJECT_ROOT / "PIPELINE.md"
    AI_CONTEXT_MD_PATH: Path = PROJECT_ROOT / "AI_CONTEXT.md"
    AGENTS_MD_PATH: Path = PROJECT_ROOT / "AGENTS.md"

    # Hermes Integration (Look for HERMES_BATCH_QUEUE in neighboring repos or env var)
    DEFAULT_HERMES_QUEUE_PATHS = [
        Path(os.environ.get("HERMES_QUEUE_FILE", "")),
        PROJECT_ROOT.parent / "mywork" / "HERMES_BATCH_QUEUE.json",
        PROJECT_ROOT.parent / "MY-WORK" / "HERMES_BATCH_QUEUE.json",
        PROJECT_ROOT / "HERMES_BATCH_QUEUE.json",
    ]

    # Standard CLI Exit Codes
    EXIT_SUCCESS: int = 0
    EXIT_ERROR: int = 1
    EXIT_NO_DATA: int = 2

    # Candidate Profile Information (Defaults)
    CANDIDATE_NAME: str = "Абдулхаким Курбанов"
    CANDIDATE_PHONE: str = "+998 90 855-07-90"
    CANDIDATE_EMAIL: str = "aa998908550790@gmail.com"
    CANDIDATE_TELEGRAM: str = "@SAWAS0078"
    CANDIDATE_LOCATION: str = "Ташкент, Узбекистан"
    SALARY_EXPECTATION_DEFAULT: str = "$1,500 - $2,500"

    # Headless Edge Executable Path for HTML -> PDF
    EDGE_PATHS = [
        Path(os.environ.get("EDGE_BIN", "")),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
    ]

    @classmethod
    def get_hermes_queue_path(cls) -> Optional[Path]:
        """Finds the first existing path to HERMES_BATCH_QUEUE.json."""
        for p in cls.DEFAULT_HERMES_QUEUE_PATHS:
            if p and p.is_file():
                return p.resolve()
        return None

    @classmethod
    def get_edge_binary(cls) -> Optional[Path]:
        """Finds msedge.exe for headless PDF rendering."""
        for p in cls.EDGE_PATHS:
            if p and p.is_file():
                return p.resolve()
        return None

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensures that required directories exist on disk."""
        for d in [
            cls.DB_DIR,
            cls.SCRIPTS_DIR,
            cls.MASTER_DIR,
            cls.VARIANTS_DIR,
            cls.TEMPLATES_DIR,
            cls.GENERATED_DIR,
            cls.LOGS_DIR,
            cls.TESTS_DIR,
            cls.SCRIPTS_DIR / "portals",
        ]:
            d.mkdir(parents=True, exist_ok=True)
