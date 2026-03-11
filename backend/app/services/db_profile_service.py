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

    def __init__(self):
        # We will determine the path to load in the _load_profiles method
        self._profiles: Dict[str, OracleProfile] = {}
        self._load_profiles()

    def list_profiles(self) -> List[OracleProfile]:
        return [self._profiles[k] for k in sorted(self._profiles.keys())]

    def get_profile(self, alias: str) -> OracleProfile:
        if alias not in self._profiles:
            raise ValueError(f"Unknown database profile alias: {alias}")
        return self._profiles[alias]

    def _load_profiles(self) -> None:
        config_dir = Path(__file__).resolve().parent.parent / "config"
        local_path = config_dir / "db_profiles.properties"
        template_path = config_dir / "db_profiles.properties.template"
        
        path_to_load = None
        if local_path.exists():
            path_to_load = local_path
        elif template_path.exists():
            path_to_load = template_path
            logger.warning("Local 'db_profiles.properties' not found. Using template file as a fallback.")
        
        if not path_to_load:
            raise FileNotFoundError(
                f"Neither 'db_profiles.properties' nor 'db_profiles.properties.template' found in {config_dir}."
            )

        parser = configparser.ConfigParser()
        parser.read(path_to_load, encoding="utf-8")

        loaded: Dict[str, OracleProfile] = {}
        for alias in parser.sections():
            section = parser[alias]
            
            password = section.get("password", "")
            # Skip profiles in the template file that have placeholder passwords
            if password == "<YOUR_PASSWORD>":
                logger.warning(f"Skipping profile [{alias}] from template file due to placeholder password.")
                continue

            host = section.get("host", "").strip()
            port = int(section.get("port", "1521"))
            service_name = section.get("service_name", section.get("serviceName", "")).strip() or None
            sid = section.get("sid", "").strip() or None
            user = section.get("user", "").strip()
            ssl = section.getboolean("ssl", fallback=False)
            label = section.get("label", "").strip() or None

            if not host:
                raise ValueError(f"Profile [{alias}] must define host.")
            if not user:
                raise ValueError(f"Profile [{alias}] must define user.")
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
        logger.info("Loaded %d DB profile(s) from %s", len(self._profiles), path_to_load)
