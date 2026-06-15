from src.infrastructure.repositories import AssetRepository
from src.domain.entities import Asset

class AssetService:
    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository

    async def save_passed_asset(self, job_id: str, url: str, title: str, snippet: str, score: float) -> None:
        asset = Asset(
            job_id=job_id,
            url=url,
            title=title,
            content_snippet=snippet,
            confidence_score=score
        )
        await self.repository.save(asset)

    async def get_assets(self, page: int, limit: int = 50) -> list[Asset]:
        return await self.repository.get_paginated(page, limit)
        
    async def get_total_count(self) -> int:
        return await self.repository.count()
