"""Utility functions for scanner."""

import re
from typing import Any, Optional


def safe_parse(value: str, pattern: str = r"^[a-zA-Z0-9_\-]+$") -> Optional[str]:
    """Parse and validate input string."""
    if not value or not isinstance(value, str):
        return None
    if re.match(pattern, value):
        return value.strip()
    return None


def retry_on_failure(func, max_retries: int = 3, delay: float = 0.5):
    """Retry decorator for async functions."""
    import asyncio
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
        raise last_error

    return wrapper


def format_result(data: Any, indent: int = 2) -> str:
    """Format result data for display."""
    import json
    return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
