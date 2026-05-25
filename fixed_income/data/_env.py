from __future__ import annotations

from pathlib import Path


def load_project_dotenv() -> bool:
    """
    Load ``fixed-income/.env`` if present (does not override existing env vars).
    Returns True if a file was loaded.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return _load_dotenv_minimal()

    for directory in (Path(__file__).resolve().parents):
        env_path = directory / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=False)
            return True
        if directory.name == "fixed-income":
            break
    return False


def _load_dotenv_minimal() -> bool:
    """Parse KEY=VALUE lines without python-dotenv."""
    for directory in (Path(__file__).resolve().parents):
        env_path = directory / ".env"
        if not env_path.is_file():
            if directory.name == "fixed-income":
                break
            continue
        import os

        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)
        return True
    return False
