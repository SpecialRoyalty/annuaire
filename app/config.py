import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _ints(value: str) -> set[int]:
    if not value:
        return set()
    return {int(x.strip()) for x in value.split(",") if x.strip().isdigit()}

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "touslesliens_bot")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPER_ADMIN_IDS: set[int] = None
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "support")
    PAGE_SIZE: int = int(os.getenv("PAGE_SIZE", "3"))
    START_STATS_MIN: int = int(os.getenv("START_STATS_MIN", "1000"))
    PENDING_CONNECT_HOURS: int = int(os.getenv("PENDING_CONNECT_HOURS", "1"))
    MAX_BOT_WARNINGS: int = int(os.getenv("MAX_BOT_WARNINGS", "3"))
    INACTIVE_DAYS_BEFORE_DELIST: int = int(os.getenv("INACTIVE_DAYS_BEFORE_DELIST", "10"))

    def __post_init__(self):
        self.SUPER_ADMIN_IDS = _ints(os.getenv("SUPER_ADMIN_IDS", ""))
        if self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        self.DATABASE_URL = self.DATABASE_URL.strip().strip('"').strip("'")

settings = Settings()
