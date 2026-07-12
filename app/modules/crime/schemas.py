from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CrimeStatsResponse(BaseModel):
    total_events: int
    categories: dict[str, int]
    last_scraper_run: Optional[str] = None
