import os
import warnings
from pathlib import Path
from typing import Literal, Optional

from pydantic import (
    computed_field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="app/.env", env_ignore_empty=True, extra="ignore"
    )
    API_V1_STR: str = "/api/v1"
    DOMAIN: str = "localhost"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    PROJECT_HOME: Path = Path(__file__).absolute().parent.parent

    @computed_field  # type: ignore[misc]
    @property
    def server_host(self) -> str:
        # Use HTTPS for anything other than local development
        if self.ENVIRONMENT == "local":
            return f"http://{self.DOMAIN}"
        return f"http://{self.DOMAIN}"

    PROJECT_NAME: Optional[str] = None

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    ASR_ENGINE: str = "faster_whisper"
    WHISPER_ASR_MODEL: str = "large-v3"
    WHISPER_ASR_MODEL_PATH: str = os.path.join(os.path.expanduser("~"), ".cache", "whisper")


settings = Settings()  # type: ignore
