from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    allowed_user_ids: str = ""

    twogis_api_key: str

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "parsing2gis"
    postgres_user: str = "postgres"
    postgres_password: str

    google_spreadsheet_id: str
    google_service_account_json: str

    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def allowed_ids(self) -> list[int]:
        if not self.allowed_user_ids:
            return []
        return [int(uid.strip()) for uid in self.allowed_user_ids.split(",") if uid.strip()]

    @property
    def google_credentials(self) -> dict:
        return json.loads(self.google_service_account_json)


settings = Settings()
