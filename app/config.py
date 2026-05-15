import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def parse_ids(value: str) -> set[int]:
    out = set()
    for x in (value or "").split(","):
        x = x.strip()
        if x.isdigit():
            out.add(int(x))
    return out

@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "touslesgroupes_bot").replace("@","")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPER_ADMIN_IDS: set[int] = None
    SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "support").replace("@","")
    PAGE_SIZE: int = int(os.getenv("PAGE_SIZE","3"))
    START_STATS_MIN: int = int(os.getenv("START_STATS_MIN","1000"))
    MAX_BOT_WARNINGS: int = int(os.getenv("MAX_BOT_WARNINGS","3"))
    PENDING_CONNECT_HOURS: int = int(os.getenv("PENDING_CONNECT_HOURS","1"))

    def __post_init__(self):
        self.SUPER_ADMIN_IDS = parse_ids(os.getenv("SUPER_ADMIN_IDS",""))
        self.DATABASE_URL = (self.DATABASE_URL or "").strip().strip('"').strip("'")
        if self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://","postgresql+asyncpg://",1)

settings = Settings()
