"""Application-wide constants and configurable limits.

Limits can be overridden with environment variables (UTP_*) so that they can be
tuned per machine without editing code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

APP_NAME = "Unit Testing Platform"
APP_PHASE = "Phase 1 · Cyclomatic Complexity Analysis"

# Initial value of the single complexity threshold input (any positive integer is accepted).
DEFAULT_THRESHOLD = 1
MIN_THRESHOLD = 1

# Prefix for temporary workspaces; used for safe cleanup of stale directories.
WORKSPACE_PREFIX = "utp_ws_"

MB = 1024 * 1024


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Limits:
    max_upload_bytes: int          # any single uploaded file (incl. a ZIP)
    max_extracted_bytes: int       # total bytes written when extracting ZIPs
    max_zip_members: int           # entries in a single ZIP
    max_source_file_bytes: int     # one source file
    max_zip_ratio: int             # uncompressed/compressed ratio per entry
    max_excel_bytes: int           # one Excel report


def load_limits() -> Limits:
    return Limits(
        max_upload_bytes=_env_int("UTP_MAX_UPLOAD_MB", 200) * MB,
        max_extracted_bytes=_env_int("UTP_MAX_EXTRACTED_MB", 500) * MB,
        max_zip_members=_env_int("UTP_MAX_ZIP_MEMBERS", 20000),
        max_source_file_bytes=_env_int("UTP_MAX_SOURCE_FILE_MB", 5) * MB,
        max_zip_ratio=_env_int("UTP_MAX_ZIP_RATIO", 200),
        max_excel_bytes=_env_int("UTP_MAX_EXCEL_MB", 25) * MB,
    )
