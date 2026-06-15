from src.config import config
from src.infrastructure.repositories import AssetRepository, JobRepository
from src.application.scoring_service import ConfidenceScoringService
from src.application.asset_service import AssetService
from src.infrastructure.crawlee_engine import CrawleeEngine
from src.application.crawl_manager import CrawlManager

class ServiceContainer:
    def __init__(self) -> None:
        self.asset_repo = AssetRepository()
        self.job_repo = JobRepository()
        self.scoring_service = ConfidenceScoringService(threshold=config.confidence_threshold)
        self.asset_service = AssetService(repository=self.asset_repo)
        
        self.crawler_engine = CrawleeEngine(
            scoring_service=self.scoring_service, 
            on_asset_created=self.asset_service.save_passed_asset
        )
        self.crawl_manager = CrawlManager(
            job_repo=self.job_repo,
            asset_service=self.asset_service,
            crawler_engine=self.crawler_engine
        )

container = ServiceContainer()
