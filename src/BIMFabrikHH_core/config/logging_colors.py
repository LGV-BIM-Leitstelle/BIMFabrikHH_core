import logging


class CustomColorFormatter(logging.Formatter):
    COLOR_MAP = {
        "db": "\033[35m",  # Purple for database debug
        "auth": "\033[34m",  # Blue for auth debug
        "file": "\033[32m",  # Green for file operations
        "network": "\033[33m",  # Yellow for network
        "ui": "\033[95m",  # Magenta for UI
        "core": "\033[31m",  # Red for core errors
        "config": "\033[94m",  # Light blue for config
        "performance": "\033[92m",  # Light green for performance
        "security": "\033[91m",  # Light red for security
        "success": "\033[32m",  # Green for success
        "default_data": "\033[90m",  # Gray fallback
    }
    RESET = "\033[0m"

    def format(self, record):
        # Safely get debug_category, defaulting to "default_data" if not present
        try:
            category = getattr(record, "debug_category", "default_data")
        except AttributeError:
            category = "default_data"
        color = self.COLOR_MAP.get(category, self.COLOR_MAP["default_data"])
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[34m",  # Blue
        "INFO": "\033[35m",  # Magenta
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def get_logger(name: str = "bimfabrikhh") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = CustomColorFormatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger


def get_level_logger(name: str = "bimfabrikhh_level") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = ColorFormatter("%(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger
