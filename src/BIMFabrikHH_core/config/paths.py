"""
Path configuration for BIMFabrikHH.

This module defines all the important paths used throughout the application.
"""

import re
from pathlib import Path

_MNT_DRIVE = re.compile(r"^/mnt/([a-zA-Z])(?:/(.*))?$")
_WIN_DRIVE = re.compile(r"^([a-zA-Z]):(?:[\\/](.*))?$")


def existing_local_dir(raw: str) -> Path | None:
    """First existing directory: Linux ``/mnt/c/…``, then Windows ``C:\\…``.

    Deployment targets Linux, so the ``/mnt`` spelling is tried first. It is
    also the safer of the two: to Linux a ``C:\\…`` string is not an absolute
    path but a single relative filename, which would resolve against the
    working directory if something ever created a directory by that name.
    """
    text = raw.strip()
    if not text:
        return None
    posix = text.replace("\\", "/")
    candidates: list[Path] = []
    mnt = _MNT_DRIVE.match(posix)
    win = _WIN_DRIVE.match(posix)
    if mnt:
        rest = (mnt.group(2) or "").replace("/", "\\")
        candidates.append(Path(posix))
        candidates.append(Path(f"{mnt.group(1).upper()}:\\" + rest))
    elif win:
        rest = win.group(2) or ""
        candidates.append(Path(f"/mnt/{win.group(1).lower()}/{rest}"))
        candidates.append(Path(f"{win.group(1).upper()}:\\" + rest.replace("/", "\\")))
    else:
        candidates.append(Path(text).expanduser())
    seen: list[Path] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.append(candidate)
        if candidate.is_dir():
            return candidate
    return None


def local_dir_or_raw(raw: str) -> str:
    """``raw`` as a directory this OS can open, else ``raw`` unchanged.

    Dataset roots are configured as Windows paths, so a Linux worker has to use
    the ``/mnt/…`` form before it can read anything beneath them. Remote
    ``http(s)://`` roots have no local directory and come back untouched, so
    callers can still fetch from them.
    """
    found = existing_local_dir(raw)
    return str(found) if found is not None else raw


class PathConfig:
    """
    Configuration class for managing file paths and constants.
    """

    _PROJECT_ROOT = Path(__file__).resolve().parents[3]

    PARENT = Path(__file__).parent
    PROJECT_ROOT = _PROJECT_ROOT
    EXAMPLES = _PROJECT_ROOT / "examples"
    ASSETS = EXAMPLES / "assets"
    OUTPUT = _PROJECT_ROOT / "output"
    SRC = _PROJECT_ROOT / "src"
    TESTS = _PROJECT_ROOT / "tests"
    TEMP = _PROJECT_ROOT / "temp"
    # Use package location for config when installed, fallback to dev path
    CONFIG = Path(__file__).parent  # This is always BIMFabrikHH_core/config/


if __name__ == "__main__":
    from BIMFabrikHH_core.config.logging_config import get_logger

    logger = get_logger("paths")

    logger.info("PROJECT_ROOT: %s", PathConfig.PROJECT_ROOT)
    logger.info("ASSETS: %s", PathConfig.ASSETS)
    logger.info("OUTPUT: %s", PathConfig.OUTPUT)
    logger.info("EXAMPLES: %s", PathConfig.EXAMPLES)
    logger.info("SRC: %s", PathConfig.SRC)
    logger.info("TESTS: %s", PathConfig.TESTS)
    logger.info("TEMP: %s", PathConfig.TEMP)
    logger.info("CONFIG: %s", PathConfig.CONFIG)
