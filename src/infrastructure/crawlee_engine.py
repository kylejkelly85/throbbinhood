from src.infrastructure.crawler_factory import CrawlerFactory
from src.application.scoring_service import ConfidenceScoringService
from src.infrastructure.logger import logger
from crawlee.crawlers import PlaywrightCrawlingContext
from typing import Callable, Awaitable, List
import os

class CrawleeEngine:
    def __init__(
        self, 
        scoring_service: ConfidenceScoringService, 
        on_asset_created: Callable[[str, str, str, str, float], Awaitable[None]]
    ) -> None:
        self.scoring_service = scoring_service
        self.on_asset_created = on_asset_created
        # Set environment variables for Chromium
        os.environ['PLAYWRIGHT_CHROMIUM_ARGS'] = '--no-sandbox --disable-setuid-sandbox'

    async def run(self, job_id: str, seed_urls: List[str], max_requests: int, target_keyword: str, file_extension: str) -> None:
        crawler = CrawlerFactory.create_playwright_crawler(max_requests)
        
        # Override browser pool options to disable sandbox
        crawler.browser_pool_options = {
            'browser_type': 'chromium',
            'headless': True,
            'launch_options': {
                'chromium_sandbox': False,
                'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            }
        }

        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            url = context.request.url.lower()
            
            # 1. Hard Extension Filtering
            # Ensure it ends with selected file extension
            if file_extension and not url.endswith(f".{file_extension.lower()}"):
                logger.debug("skipped_wrong_extension", url=context.request.url)
                return

            context.log.info(f"Processing target file {context.request.url}")
            
            # 2. In-Memory Buffer Parsing
            # Stream the first 10KB to check for target_keyword
            has_keyword = False
            title = ""
            content_snippet = ""
            text = ""
            
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Range": "bytes=0-10240"}
                    async with session.get(context.request.url, headers=headers, timeout=10) as response:
                        buffer = await response.read()
                        text = buffer.decode(errors='ignore').lower()
                        title_candidate = url.split("/")[-1]
                        title = title_candidate if title_candidate else "Unknown Document"
                        content_snippet = text[:200]
                        
                        if target_keyword.lower() in text:
                            has_keyword = True
            except Exception as e:
                logger.debug("buffer_parse_failed", error=str(e), url=context.request.url)

            # 3. Reject on mismatch
            if not has_keyword:
                logger.debug("asset_dropped_missing_keyword", url=context.request.url, keyword=target_keyword)
                return

            # Apply Scoring logic prioritize target_keyword
            # evaluate should take url, content, and the target keyword
            score = self.scoring_service.evaluate(context.request.url, text, target_keyword)
            
            if self.scoring_service.passes_gate(score):
                logger.info("asset_passed_gate", url=context.request.url, score=score)
                await self.on_asset_created(job_id, context.request.url, title, content_snippet, score)
            else:
                logger.debug("asset_failed_gate", url=context.request.url, score=score)

        await crawler.run(seed_urls)