from pydantic import BaseModel, ConfigDict
from .value_objects import CrawlStateEnum
from typing import List, Optional

class CrawlJob(BaseModel):
    id: Optional[str] = None
    seed_urls: List[str]
    max_requests: int
    state: CrawlStateEnum = CrawlStateEnum.PENDING

    model_config = ConfigDict(from_attributes=True)

class Asset(BaseModel):
    id: Optional[str] = None
    job_id: str
    url: str
    title: str
    content_snippet: str
    confidence_score: float
    is_downloaded: bool = False

    model_config = ConfigDict(from_attributes=True)
