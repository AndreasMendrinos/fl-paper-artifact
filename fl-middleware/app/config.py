from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


ProviderMode = Literal["mock", "live", "disabled"]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "FL Resource Middleware"
    app_version: str = "0.1.0"
    app_env: str = "development"

    iotlab_enabled: bool = True
    iotlab_mode: ProviderMode = "mock"
    iotlab_api_url: str = "https://www.iot-lab.info/api"
    iotlab_username: str | None = None
    iotlab_password: str | None = None
    iotlab_sites: str = "auto"
    iotlab_include_native_data: bool = False

    chameleon_enabled: bool = True
    chameleon_mode: ProviderMode = "mock"
    chameleon_discovery_url: str = "https://api.chameleoncloud.org"
    #chameleon_sites: str = "tacc,uc,ncar,nu,nrp"
    chameleon_sites: str = "auto"
    chameleon_site_classes: str = "baremetal"
    chameleon_clusters: str = "auto"

    chameleon_request_timeout_seconds: float = 30.0
    chameleon_max_connections: int = 10
    chameleon_verify_ssl: bool = True
    chameleon_include_native_data: bool = False

    chameleon_auth_enabled: bool = False
    chameleon_auth_type: str = "v3applicationcredential"
    chameleon_auth_url: str | None = None
    chameleon_region_name: str | None = None
    chameleon_interface: str = "public"

    chameleon_application_credential_id: str | None = None
    chameleon_application_credential_secret: str | None = None

    chameleon_key_name: str | None = None

    chameleon_image_name: str = (
        "CC-Ubuntu22.04"
    )

    chameleon_network_name: str = (
        "sharednet1"
    )

    chameleon_ssh_username: str = "cc"

    grid5000_enabled: bool = True
    grid5000_mode: ProviderMode = "mock"
    grid5000_api_url: str = "https://api.grid5000.fr/stable"
    grid5000_username: str | None = None
    grid5000_password: str | None = None
    grid5000_sites: str = "auto"
    grid5000_include_native_data: bool = False
    grid5000_request_timeout_seconds: float = 30.0
    grid5000_max_connections: int = 10
    grid5000_verify_ssl: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()