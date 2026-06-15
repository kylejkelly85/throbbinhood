from crawlee.crawlers import PlaywrightCrawler, HttpCrawler

class CrawlerFactory:
    @staticmethod
    def create_playwright_crawler(max_requests: int) -> PlaywrightCrawler:
        return PlaywrightCrawler(max_requests_per_crawl=max_requests)

    @staticmethod
    def create_http_crawler(max_requests: int) -> HttpCrawler:
        return HttpCrawler(max_requests_per_crawl=max_requests)
