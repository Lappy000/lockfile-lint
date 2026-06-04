"""Version management."""

__version__ = "0.1.0"


def get_version_info() -> dict:
    """Return version metadata."""
    return {
        "version": __version__,
        "python_minimum": "3.9",
        "malicious_db_version": "2026.05.20",
    }
