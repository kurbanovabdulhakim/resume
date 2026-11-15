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

    # Hermes Integration & Local Autonomy Runtime Paths
    DATA_DIR = PROJECT_ROOT / "data"
    HH_QUEUE_FILE = Path(os.environ.get("HH_QUEUE_FILE") or (DATA_DIR / "hh_autonomy_queue.json"))
    HH_STATE_FILE = Path(os.environ.get("HH_STATE_FILE") or (DATA_DIR / "hh_autonomy_state.json"))
    HH_SESSION_PROFILE_DIR = Path(
        os.environ.get("HH_PROFILE_DIR") or (Path.home() / ".gemini" / "hh_main_session")
    )

    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
    OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "12288"))

    DEFAULT_HERMES_QUEUE_PATHS = [
        p
        for p in [
            Path(os.environ["HERMES_QUEUE_FILE"]) if os.environ.get("HERMES_QUEUE_FILE", "").strip() else None,
            PROJECT_ROOT / "HERMES_BATCH_QUEUE.json",
            DATA_DIR / "hermes_batch_queue.json",
        ]
        if p is not None
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

    # Typst Executable Paths
    TYPST_PATHS = [
        Path(os.environ.get("TYPST_BIN", "")),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages" / "Typst.Typst_Microsoft.Winget.Source_8wekyb3d8bbwe" / "typst-x86_64-pc-windows-msvc" / "typst.exe",
    ]

    @classmethod
    def get_hermes_queue_path(cls) -> Optional[Path]:
        """Finds the first existing path to HERMES_BATCH_QUEUE.json."""
        for p in cls.DEFAULT_HERMES_QUEUE_PATHS:
            if p and p.is_file():
                return p.resolve()
        return None

    @classmethod
    def get_typst_binary(cls) -> Optional[Path]:
        """Finds typst.exe binary for ultra-fast vector PDF rendering."""
        import shutil
        which_path = shutil.which("typst")
        if which_path:
            return Path(which_path).resolve()
        for p in cls.TYPST_PATHS:
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
            cls.DATA_DIR,
            cls.TESTS_DIR,
            cls.SCRIPTS_DIR / "portals",
        ]:
            d.mkdir(parents=True, exist_ok=True)
