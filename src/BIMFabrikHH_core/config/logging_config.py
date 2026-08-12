"""
Centralized logging configuration for BIMFabrikHH core.

Provides a single standardized logger for the whole package via
:func:`get_logger`. Following the standard library-logging convention, importing
and using :func:`get_logger` never configures handlers by itself: the base
``bimfabrikhh_core`` logger only carries a :class:`~logging.NullHandler` and lets
its records propagate to whatever the *application* configures on the root
logger. This lets BIMFabrikHH_core be embedded in another application (such as
the BIMFabrikHH_api) where the host owns the handlers and both console and file
output are shared.

For standalone use (examples, scripts, ``__main__`` blocks), call
:func:`setup_logging` once at the entry point. It attaches:

* a console (stream) handler, and
* an optional time-rotating file handler writing to a shared log file.

Both handlers have independently configurable log levels, and all values are
sourced from the logging settings (which load from ``.env``).

The optional ``debug_category`` record attribute is preserved for callers that
want to tag records (e.g. ``logger.info("msg", extra={"debug_category": "db"})``);
the category is appended to the message when present. Coloring is intentionally
not applied.
"""

import logging
import logging.handlers
from pathlib import Path

from .settings import PROJECT_ROOT, logging_settings

# Log record format shared by both handlers.
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Base logger name; all module loggers are children of this logger.
ROOT_LOGGER_NAME = "bimfabrikhh_core"

# Sentinel value for records without an explicit category.
_DEFAULT_CATEGORY = "default_data"

# Guard so repeated calls within a single process do not rebuild the config.
_configured = False

# Attach a NullHandler so that merely importing and using the library never
# configures handlers or emits "No handlers could be found" warnings. When core
# runs inside a host application (e.g. the BIMFabrikHH_api), records propagate to
# the root logger and are handled by the host's console and file handlers.
logging.getLogger(ROOT_LOGGER_NAME).addHandler(logging.NullHandler())


class CategoryFormatter(logging.Formatter):
    """Formatter that appends an optional ``debug_category`` tag.

    Records carrying a non-default ``debug_category`` attribute are suffixed with
    ``- [<category>]`` so the category remains visible in both console and file
    output. No ANSI coloring is applied.
    """

    def format(self, record: logging.LogRecord) -> str:
        category = getattr(record, "debug_category", _DEFAULT_CATEGORY)
        message = super().format(record)
        if category and category != _DEFAULT_CATEGORY:
            message = f"{message} - [{category}]"
        return message


def _resolve_log_file_path() -> Path:
    """Return the absolute log file path, resolving relative paths.

    Relative ``LOG_FILE_PATH`` values are resolved against the project root so
    behaviour is independent of the current working directory.
    """
    configured = Path(logging_settings.LOG_FILE_PATH)
    if not configured.is_absolute():
        configured = PROJECT_ROOT / configured
    return configured


def setup_logging(force: bool = False) -> None:
    """Configure standalone package-wide logging.

    Intended for standalone use of BIMFabrikHH_core (examples, scripts,
    ``__main__`` blocks). Sets up the ``bimfabrikhh_core`` logger with a console
    handler and, when enabled, a time-rotating file handler, and stops
    propagation so the logger owns its output. The function is idempotent:
    subsequent calls within the same process are ignored unless ``force`` is
    ``True``.

    When BIMFabrikHH_core is embedded in a host application (e.g. the BIMFabrikHH_api), do
    **not** call this function: leave the base logger on its NullHandler so
    records propagate to the host's root handlers.

    Args:
        force: Rebuild the configuration even if logging was already set up in
            this process.
    """
    global _configured
    if _configured and not force:
        return

    console_level = logging_settings.LOG_LEVEL_CONSOLE.upper()
    file_level = logging_settings.LOG_LEVEL_FILE.upper()

    logger = logging.getLogger(ROOT_LOGGER_NAME)
    # Remove any previously attached handlers so repeated (forced) calls do not
    # accumulate duplicate handlers.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = CategoryFormatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    active_levels = [console_level]

    if logging_settings.LOG_FILE_ENABLED:
        log_file = _resolve_log_file_path()
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(log_file),
                when=logging_settings.LOG_FILE_WHEN,
                backupCount=logging_settings.LOG_FILE_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(file_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            active_levels.append(file_level)
        except OSError as exc:
            # A logging/file problem (e.g. the log file is not writable) must
            # never prevent the application from starting. Fall back to
            # console-only logging and continue.
            logger.warning(
                "Could not configure file log handler for %s (%s); " "falling back to console logging only.",
                log_file,
                exc,
            )

    # Logger must be at least as verbose as the most verbose handler, otherwise
    # records are filtered out before reaching the handlers.
    root_level = min(logging.getLevelName(lvl) for lvl in active_levels)
    logger.setLevel(root_level)
    logger.propagate = False

    _configured = True


def get_logger(name: str = ROOT_LOGGER_NAME) -> logging.Logger:
    """Return a logger for the given ``name``.

    Returns either the base ``bimfabrikhh_core`` logger or a child of it. This
    function never configures handlers: records propagate to whatever the host
    application (or :func:`setup_logging` for standalone use) has configured.

    Args:
        name: Logger name. When it equals the base name (default), the base
            logger is returned; otherwise a child logger
            ``bimfabrikhh_core.<name>``.
    """
    if name == ROOT_LOGGER_NAME:
        return logging.getLogger(ROOT_LOGGER_NAME)
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
