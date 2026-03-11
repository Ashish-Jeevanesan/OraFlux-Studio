from pathlib import Path

import pytest

from app.services.db_profile_service import DbProfileService


def test_loads_profiles_from_properties():
    config_file = Path(__file__).parent / "fixtures" / "db_profiles_test.properties"
    service = DbProfileService(config_path=str(config_file))
    profiles = service.list_profiles()

    assert len(profiles) == 1
    assert profiles[0].alias == "DEV1"
    assert profiles[0].label == "Dev One"
    assert profiles[0].service_name == "ORCLPDB1"


def test_unknown_alias_raises():
    config_file = Path(__file__).parent / "fixtures" / "db_profiles_test.properties"
    service = DbProfileService(config_path=str(config_file))

    with pytest.raises(ValueError, match="Unknown database profile alias"):
        service.get_profile("MISSING")
