from src.infrastructure.crawler_factory import CrawlerFactory
from src.application.scoring_service import ConfidenceScoringService
from src.infrastructure.logger import logger
from crawlee.crawlers import PlaywrightCrawlingContext
from typing import Callable, Awaitable, List

class CrawleeEngine:
    def __init__(
        self, 
        scoring_service: ConfidenceScoringService, 
        on_asset_created: Callable[[str, str, str, str, float], Awaitable[None]]
    ) -> None:
        self.scoring_service = scoring_service
        self.on_asset_created = on_asset_created

    async def run(self, job_id: str, seed_urls: List[str], max_requests: int) -> None:
        crawler = CrawlerFactory.create_playwright_crawler(max_requests)

        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            context.log.info(f"Processing {context.request.url}")
            title = await context.page.title()
            content = await context.page.evaluate("document.body.innerText")
            content_snippet = content[:200]
            
            score = self.scoring_service.evaluate(title, content)
            
            if self.scoring_service.passes_gate(score):
                logger.info("asset_passed_gate", url=context.request.url, score=score)
                await self.on_asset_created(job_id, context.request.url, title, content_snippet, score)
            else:
                logger.debug("asset_failed_gate", url=context.request.url, score=score)

        await crawler.run(seed_urls)
