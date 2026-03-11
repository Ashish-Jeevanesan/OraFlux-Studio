import logging
import os
from pathlib import Path
from typing import Any, Dict

import oracledb


logger = logging.getLogger(__name__)

DEFAULT_WINDOWS_CLIENT_DIRS = [
    r"C:\Program Files\oracle\instantclient_21_20",
]


def initialize_oracle_client() -> bool:
    """
    Try to enable python-oracledb Thick mode before any pools are created.

    Returns True when Thick mode is active, otherwise False. If
    ORACLE_REQUIRE_THICK_MODE is set to a truthy value, startup fails when
    the Oracle Client libraries cannot be loaded.
    """
    if not oracledb.is_thin_mode():
        logger.info("python-oracledb is already running in Thick mode.")
        return True

    require_thick = os.getenv("ORACLE_REQUIRE_THICK_MODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    lib_dir = _clean_env("ORACLE_CLIENT_LIB_DIR") or _detect_default_client_dir()
    config_dir = _clean_env("ORACLE_NET_CONFIG_DIR") or _clean_env("TNS_ADMIN")
    if not config_dir and lib_dir:
        candidate = Path(lib_dir) / "network" / "admin"
        if candidate.exists():
            config_dir = str(candidate)

    if lib_dir:
        _prepend_windows_path(lib_dir)

    kwargs: Dict[str, Any] = {
        "driver_name": "OraFlux Studio : 1.1.0",
    }
    if lib_dir:
        kwargs["lib_dir"] = lib_dir
    if config_dir:
        kwargs["config_dir"] = config_dir

    try:
        oracledb.init_oracle_client(**kwargs)
        logger.info(
            "Initialized python-oracledb Thick mode. lib_dir=%r config_dir=%r",
            lib_dir,
            config_dir,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Unable to initialize python-oracledb Thick mode. "
            "Continuing in Thin mode. lib_dir=%r config_dir=%r error=%s",
            lib_dir,
            config_dir,
            exc,
        )
        if require_thick:
            raise RuntimeError(
                "Oracle Thick mode is required but could not be initialized. "
                "Set ORACLE_CLIENT_LIB_DIR to your Instant Client directory and "
                "optionally ORACLE_NET_CONFIG_DIR or TNS_ADMIN for network config."
            ) from exc
        return False


def _clean_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _detect_default_client_dir() -> str | None:
    for path in DEFAULT_WINDOWS_CLIENT_DIRS:
        if Path(path).exists():
            return path
    return None


def _prepend_windows_path(lib_dir: str) -> None:
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    normalized = {part.lower() for part in path_parts}
    if lib_dir.lower() not in normalized:
        os.environ["PATH"] = lib_dir + os.pathsep + current_path if current_path else lib_dir
