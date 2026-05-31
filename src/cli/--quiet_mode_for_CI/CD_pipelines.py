"""--quiet mode for ci/cd pipelines."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CliHandler:
    """Handle --quiet mode for CI/CD pipelines operations."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._initialized = False

    async def execute(self, *args, **kwargs):
        """Execute the --quiet mode for CI/CD pipelines operation."""
        logger.debug("Starting %s", "--quiet mode for CI/CD pipelines")
        try:
            result = await self._run(*args, **kwargs)
            self._initialized = True
            return result
        except Exception as e:
            logger.error("Failed: %s", e)
            raise

    async def _run(self, *args, **kwargs):
        """Internal implementation."""
        raise NotImplementedError

    @property
    def is_ready(self) -> bool:
        return self._initialized
