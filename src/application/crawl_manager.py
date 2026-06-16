from src.infrastructure.repositories import JobRepository
from src.application.asset_service import AssetService
from src.infrastructure.crawlee_engine import CrawleeEngine
from src.domain.entities import CrawlJob
from src.domain.value_objects import CrawlStateEnum
import uuid
import asyncio
from typing import List
from src.infrastructure.logger import logger

class CrawlManager:
    def __init__(self, job_repo: JobRepository, asset_service: AssetService, crawler_engine: CrawleeEngine) -> None:
        self.job_repo = job_repo
        self.asset_service = asset_service
        self.crawler_engine = crawler_engine

    async def start_crawl(self, seed_urls: List[str], target_keyword: str, file_extension: str, max_requests: int) -> str:
        job_id = str(uuid.uuid4())
        job = CrawlJob(
            id=job_id, 
            seed_urls=seed_urls, 
            target_keyword=target_keyword,
            file_extension=file_extension,
            max_requests=max_requests, 
            state=CrawlStateEnum.RUNNING
        )
        await self.job_repo.save(job)
        
        # Dispatch background work via AsyncIO
        asyncio.create_task(self._run_crawl(job))
        return job_id
        
    async def _run_crawl(self, job: CrawlJob) -> None:
        try:
            # We can guarantee job.id exists at this stage
            job_id_str = str(job.id)
            await self.crawler_engine.run(job_id_str, job.seed_urls, job.max_requests, job.target_keyword, job.file_extension)
            job.state = CrawlStateEnum.COMPLETED
        except Exception as e:
            logger.error("crawl_failed", job_id=job.id, error=str(e), exc_info=True)
            job.state = CrawlStateEnum.FAILED
        finally:
            await self.job_repo.save(job)
