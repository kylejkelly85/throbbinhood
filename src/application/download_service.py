from src.infrastructure.download_manager import DownloadManager
from src.infrastructure.repositories import AssetRepository

class DownloadService:
    def __init__(self, download_manager: DownloadManager, asset_repo: AssetRepository) -> None:
        self.download_manager = download_manager
        self.asset_repo = asset_repo

    async def execute_download(self, asset_id: str) -> str:
        asset = await self.asset_repo.get_by_id(asset_id)
        if not asset:
            raise ValueError(f"Asset with id {asset_id} not found")
        
        # Derive filename from url or id
        filename = f"{asset.id}.pdf"
        if asset.url.split("/")[-1]:
            filename = asset.url.split("/")[-1]
            
        filepath = await self.download_manager.stream_download(asset.url, filename)
        asset.is_downloaded = True
        await self.asset_repo.save(asset)
        return filepath
