import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    runpod_api_key: str
    vast_api_key: str
    fetch_interval_hours: float
    database_url: str

    @classmethod
    def from_env(cls) -> "Config":
        runpod_key = os.getenv("RUNPOD_API_KEY", "")
        vast_key = os.getenv("VAST_API_KEY", "")
        interval = float(os.getenv("FETCH_INTERVAL_HOURS", "6"))
        database_url = os.getenv("DATABASE_URL", "")

        return cls(
            runpod_api_key=runpod_key,
            vast_api_key=vast_key,
            fetch_interval_hours=interval,
            database_url=database_url,
        )

    def validate_keys(self) -> list[str]:
        missing = []
        if not self.runpod_api_key or self.runpod_api_key.startswith("rpa_your"):
            missing.append("RUNPOD_API_KEY")
        if not self.vast_api_key or self.vast_api_key.startswith("your_vast"):
            missing.append("VAST_API_KEY")
        if not self.database_url or self.database_url.startswith("postgresql://user:password"):
            missing.append("DATABASE_URL")
        return missing

    def database_host(self) -> str:
        match = re.search(r"@([^/?]+)", self.database_url)
        return match.group(1) if match else "unknown"
