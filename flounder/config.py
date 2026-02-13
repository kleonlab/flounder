"""Configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = ""

    # Google Sheets
    google_sheets_id: str = ""
    google_service_account_file: str = "service_account.json"

    # Buckets — comma-separated list of category names
    buckets: str = "Tech,Finance,Health,News,Shopping,Travel,Other"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def bucket_list(self) -> list[str]:
        return [b.strip() for b in self.buckets.split(",") if b.strip()]


settings = Settings()
