from enum import Enum
from pydantic import BaseModel
from typing import List

class CrawlStateEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SearchConfig(BaseModel):
    seed_urls: List[str]
    target_keyword: str
    file_extension: str
    max_requests: int = 100
