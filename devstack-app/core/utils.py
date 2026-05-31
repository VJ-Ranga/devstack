"""Shared low-level helpers used across core modules."""
import os
import subprocess
import zipfile
from pathlib import Path


def no_window_flags() -> int:
    """Return CREATE_NO_WINDOW on Windows, 0 on other platforms."""
    return subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0


def safe_extractall(zip_ref: zipfile.ZipFile, target_dir: Path) -> None:
    """Extract a zip file while blocking Zip Slip path traversal attacks."""
    resolved = target_dir.resolve()
    for member in zip_ref.infolist():
        member_path = (resolved / member.filename).resolve()
        if not str(member_path).startswith(str(resolved) + os.sep):
            raise RuntimeError(
                f"Zip Slip blocked — unsafe path in archive: {member.filename}"
            )
        zip_ref.extract(member, resolved)
