"""
Pydantic settings configuration for BIMFabrikHH core.

Reads logging-related environment variables from the project ``.env`` file with
fallback to sensible defaults. Mirrors the settings approach used in the
BIMFabrikHH_api repository, so both projects share the same configuration surface.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

from .paths import PathConfig

# Project root directory used to resolve the ``.env`` file and relative log paths.
PROJECT_ROOT = PathConfig.PROJECT_ROOT


class LoggingSettings(BaseSettings):
    """Logging configuration settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Per-handler log levels (console and file handlers can differ).
    LOG_LEVEL_CONSOLE: str = "INFO"
    LOG_LEVEL_FILE: str = "INFO"
    # Whether the rotating file handler is attached at all.
    LOG_FILE_ENABLED: bool = True
    # Path (relative to project root or absolute) of the shared log file.
    LOG_FILE_PATH: str = "logs/bimfabrikhh.log"
    # Timed-rotation interval keyword (see TimedRotatingFileHandler ``when``),
    # e.g. "midnight", "H", "D", "S". Number of rotated files kept as backups.
    LOG_FILE_WHEN: str = "midnight"
    LOG_FILE_BACKUP_COUNT: int = 14


# Global settings instance
logging_settings = LoggingSettings()
