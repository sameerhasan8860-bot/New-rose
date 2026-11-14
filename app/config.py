from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    database_url: str = "sqlite+aiosqlite:///./master_x.db"
    log_level: str = "INFO"
    global_owner_ids: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def owner_ids(self) -> set[int]:
        return {int(value.strip()) for value in self.global_owner_ids.split(",") if value.strip()}
