from src.infrastructure.download_manager import DownloadManager
from src.infrastructure.repositories import AssetRepository

class DownloadService:
    def __init__(self, download_manager: DownloadManager, asset_repo: AssetRepository) -> None:
        self.download_manager = download_manager
        self.asset_repo = asset_repo

    async def download_asset(self, asset_id: str, url: str) -> str:
        filepath = await self.download_manager.stream_download(url, asset_id)
        # Update asset DB model in production architecture
        return filepath
