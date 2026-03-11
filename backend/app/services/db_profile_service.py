import configparser
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OracleProfile:
    alias: str
    host: str
    port: int
    service_name: Optional[str]
    sid: Optional[str]
    user: str
    password: str
    ssl: bool
    label: Optional[str] = None


class DbProfileService:
    """Loads and serves backend-managed Oracle connection profiles."""

    def __init__(self, config_path: Optional[str] = None):
        default_path = Path(__file__).resolve().parent.parent / "config" / "db_profiles.properties"
        self._config_path = Path(config_path or os.getenv("DB_PROFILES_FILE", str(default_path)))
        self._profiles: Dict[str, OracleProfile] = {}
        self._load_profiles()

    def list_profiles(self) -> List[OracleProfile]:
        return [self._profiles[k] for k in sorted(self._profiles.keys())]

    def get_profile(self, alias: str) -> OracleProfile:
        if alias not in self._profiles:
            raise ValueError(f"Unknown database profile alias: {alias}")
        return self._profiles[alias]

    def _load_profiles(self) -> None:
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Profile config file not found: {self._config_path}. "
                "Create it or set DB_PROFILES_FILE."
            )

        parser = configparser.ConfigParser()
        parser.read(self._config_path, encoding="utf-8")

        loaded: Dict[str, OracleProfile] = {}
        for alias in parser.sections():
            section = parser[alias]

            host = section.get("host", "").strip()
            port = int(section.get("port", "1521"))
            service_name = section.get("service_name", section.get("serviceName", "")).strip() or None
            sid = section.get("sid", "").strip() or None
            user = section.get("user", "").strip()
            password = section.get("password", "")
            ssl = section.getboolean("ssl", fallback=False)
            label = section.get("label", "").strip() or None

            if not host:
                raise ValueError(f"Profile [{alias}] must define host.")
            if not user:
                raise ValueError(f"Profile [{alias}] must define user.")
            if not password:
                raise ValueError(f"Profile [{alias}] must define password.")
            if not service_name and not sid:
                raise ValueError(f"Profile [{alias}] must define either service_name or sid.")

            loaded[alias] = OracleProfile(
                alias=alias,
                host=host,
                port=port,
                service_name=service_name,
                sid=sid,
                user=user,
                password=password,
                ssl=ssl,
                label=label,
            )

        self._profiles = loaded
        logger.info("Loaded %d DB profile(s) from %s", len(self._profiles), self._config_path)
