from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    SUPER_ADMIN_IDS: str = ""
    WEBHOOK_URL: str | None = None
    WEBHOOK_SECRET: str = "change-me"
    PORT: int = 8080
    BOT_USERNAME: str = "touslesliens_bot"

    @property
    def super_admin_ids(self) -> set[int]:
        ids: set[int] = set()
        for item in self.SUPER_ADMIN_IDS.split(','):
            item = item.strip()
            if item.isdigit():
                ids.add(int(item))
        return ids

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
