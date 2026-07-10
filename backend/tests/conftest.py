from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


TEST_ROOT = Path(tempfile.mkdtemp(prefix="avento-tests-"))
os.environ["AVENTO_ENVIRONMENT"] = "test"
os.environ["AVENTO_DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["AVENTO_UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["AVENTO_WEATHER_PROVIDER"] = "disabled"
os.environ["AVENTO_SECRET_KEY"] = "test-secret-that-is-long-enough-for-jwt-signing"
os.environ["AVENTO_AUTO_CREATE_SCHEMA"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


SAMPLE_TCX = b"""<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
 xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
 <Activities><Activity Sport="Biking"><Id>2026-06-01T08:00:00Z</Id><Lap StartTime="2026-06-01T08:00:00Z"><Track>
  <Trackpoint><Time>2026-06-01T08:00:00Z</Time><Position><LatitudeDegrees>52.5</LatitudeDegrees><LongitudeDegrees>13.4</LongitudeDegrees></Position><AltitudeMeters>100</AltitudeMeters><DistanceMeters>0</DistanceMeters><HeartRateBpm><Value>100</Value></HeartRateBpm><Cadence>70</Cadence><Extensions><ns3:TPX><ns3:Speed>0</ns3:Speed><ns3:Watts>100</ns3:Watts></ns3:TPX></Extensions></Trackpoint>
  <Trackpoint><Time>2026-06-01T08:01:00Z</Time><Position><LatitudeDegrees>52.501</LatitudeDegrees><LongitudeDegrees>13.404</LongitudeDegrees></Position><AltitudeMeters>105</AltitudeMeters><DistanceMeters>300</DistanceMeters><HeartRateBpm><Value>130</Value></HeartRateBpm><Cadence>80</Cadence><Extensions><ns3:TPX><ns3:Speed>5</ns3:Speed><ns3:Watts>180</ns3:Watts></ns3:TPX></Extensions></Trackpoint>
  <Trackpoint><Time>2026-06-01T08:02:00Z</Time><Position><LatitudeDegrees>52.501</LatitudeDegrees><LongitudeDegrees>13.404</LongitudeDegrees></Position><AltitudeMeters>105</AltitudeMeters><DistanceMeters>300</DistanceMeters><HeartRateBpm><Value>140</Value></HeartRateBpm><Cadence>75</Cadence><Extensions><ns3:TPX><ns3:Speed>0</ns3:Speed><ns3:Watts>0</ns3:Watts></ns3:TPX></Extensions></Trackpoint>
  <Trackpoint><Time>2026-06-01T08:03:00Z</Time><Position><LatitudeDegrees>52.502</LatitudeDegrees><LongitudeDegrees>13.408</LongitudeDegrees></Position><AltitudeMeters>110</AltitudeMeters><DistanceMeters>600</DistanceMeters><HeartRateBpm><Value>160</Value></HeartRateBpm><Cadence>85</Cadence><Extensions><ns3:TPX><ns3:Speed>5</ns3:Speed><ns3:Watts>220</ns3:Watts></ns3:TPX></Extensions></Trackpoint>
 </Track></Lap></Activity></Activities>
</TrainingCenterDatabase>"""


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    settings.bootstrap_invite_code = None
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "very-secure-password", "display_name": "Admin"},
    )
    assert response.status_code == 201, response.text
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}

