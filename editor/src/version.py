"""Application version module.

In development: derives version from VERSION file + git commit count since last tag.
In frozen builds: uses _BAKED_VERSION written by the build script before PyInstaller runs.
"""

import sys

# This line is overwritten by the build script before PyInstaller runs.
# In development it stays as None and we derive from git + VERSION file.
_BAKED_VERSION = None


def get_version() -> str:
    """Get the application version string (e.g. '1.3.1').
    
    Returns baked version in frozen builds, or git-derived version in dev.
    """
    if _BAKED_VERSION is not None:
        return _BAKED_VERSION
    return _dev_version()


def _dev_version() -> str:
    """Derive version from VERSION file and git describe (dev only)."""
    import subprocess
    from pathlib import Path

    # VERSION file is at project root (editor/src/version.py -> ../../VERSION -> project root)
    version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
    try:
        major_minor = version_file.read_text().strip()
    except FileNotFoundError:
        major_minor = "0.0"

    # Get commit count since last tag
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--long'],
            capture_output=True, text=True, check=False,
            cwd=str(version_file.parent),
        )
        if result.returncode == 0:
            # Format: v1.3-5-gabcdef  ->  parts[-2] = commit count
            parts = result.stdout.strip().rsplit('-', 2)
            if len(parts) == 3:
                return f"{major_minor}.{parts[1]}"
    except FileNotFoundError:
        pass  # git not installed

    # Fallback: total commit count
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            capture_output=True, text=True, check=False,
            cwd=str(version_file.parent),
        )
        if result.returncode == 0:
            return f"{major_minor}.{result.stdout.strip()}"
    except FileNotFoundError:
        pass

    return f"{major_minor}.0"
