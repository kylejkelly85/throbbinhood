from src.infrastructure.crawler_factory import CrawlerFactory
from src.application.scoring_service import ConfidenceScoringService
from src.infrastructure.logger import logger
from crawlee.crawlers import PlaywrightCrawlingContext
from typing import Callable, Awaitable, List
import os
from urllib.parse import urlparse

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

        # Extract base domains from seed URLs to keep the crawl on-site
        allowed_domains = {urlparse(url).netloc for url in seed_urls}

        @crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            url = context.request.url
            url_lower = url.lower()
            ext_lower = file_extension.lower()

            logger.info("handler_called", url=url)

            # --- CASE 1: IT'S A TARGET FILE ---
            if file_extension and url_lower.endswith(f".{ext_lower}"):
                logger.info("processing_file", url=url)

                has_keyword = False
                title = ""
                content_snippet = ""
                text = ""

                import aiohttp
                try:
                    async with aiohttp.ClientSession() as session:
                        headers = {"Range": "bytes=0-10240"}
                        async with session.get(url, headers=headers, timeout=10) as response:
                            buffer = await response.read()
                            text = buffer.decode(errors='ignore').lower()
                            title_candidate = url.split("/")[-1]
                            title = title_candidate if title_candidate else "Unknown Document"
                            content_snippet = text[:200]

                            if target_keyword.lower() in text:
                                has_keyword = True
                except Exception as e:
                    logger.info("buffer_parse_failed", error=str(e), url=url)
                    return

                if not has_keyword:
                    logger.info("asset_dropped_missing_keyword", url=url, keyword=target_keyword)
                    return

                score = self.scoring_service.evaluate(url, text, target_keyword)
                logger.info("asset_scored", url=url, score=score, threshold=self.scoring_service.threshold)

                if self.scoring_service.passes_gate(score):
                    logger.info("asset_passed_gate", url=url, score=score)
                    await self.on_asset_created(job_id, url, title, content_snippet, score)
                else:
                    logger.info("asset_failed_gate", url=url, score=score)

            # --- CASE 2: IT'S AN HTML PAGE ---
            else:
                logger.info("enqueuing_links_from_page", url=url)
        
                # Extract ALL links from the page
                all_links = await context.page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a[href]")).map(a => a.href);
                }''')

                file_links = []
                html_links = []

                for link in all_links:
                    link_lower = link.lower()
                    parsed_link = urlparse(link)
                    
                    # Ensure we stay within the seed domain scope
                    if parsed_link.netloc not in allowed_domains:
                        continue

                    # Classify the link
                    if file_extension and link_lower.endswith(f".{ext_lower}"):
                        file_links.append(link)
                    # Simple heuristic: ignore common media/assets, accept web pages
                    elif not any(link_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.zip', '.css', '.js']):
                        html_links.append(link)

                logger.info("links_classified", url=url, files_found=len(file_links), html_pages_found=len(html_links))

                # Enqueue everything found to the request queue
                for link in (file_links + html_links):
                    await context.add_requests([link])

        await crawler.run(seed_urls)