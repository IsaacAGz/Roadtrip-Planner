from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str
    openweather_api_key: str = ""
    nominatim_user_agent: str = "RoadtripPlanner/1.0"
    osrm_base_url: str = "https://router.project-osrm.org"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    wikipedia_api_url: str = "https://en.wikipedia.org/w/api.php"
    overpass_api_url: str = "https://overpass-api.de/api/interpreter"
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"
    openai_model: str = "gpt-4o-mini"
    poi_provider: Literal["osm", "google_places"] = "osm"
    google_places_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
