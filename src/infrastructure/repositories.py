from sqlalchemy import select, func
from src.infrastructure.database import async_session_maker, CrawlJobModel, AssetModel
from src.domain.entities import CrawlJob, Asset
from typing import List
import uuid
import json

class AssetRepository:
    async def save(self, asset: Asset) -> None:
        async with async_session_maker() as session:
            if asset.id:
                model = await session.get(AssetModel, asset.id)
                if model:
                    model.is_downloaded = asset.is_downloaded
                    model.confidence_score = asset.confidence_score
                    await session.commit()
                    return
            
            model = AssetModel(
                id=asset.id or str(uuid.uuid4()),
                job_id=asset.job_id,
                url=asset.url,
                title=asset.title,
                content_snippet=asset.content_snippet,
                confidence_score=asset.confidence_score,
                is_downloaded=asset.is_downloaded
            )
            session.add(model)
            await session.commit()
            if not asset.id:
                asset.id = model.id

    async def get_by_id(self, asset_id: str) -> Asset | None:
        async with async_session_maker() as session:
            model = await session.get(AssetModel, asset_id)
            return Asset.model_validate(model) if model else None
            
    async def get_paginated(self, page: int, limit: int = 50) -> List[Asset]:
        offset = (page - 1) * limit
        async with async_session_maker() as session:
            result = await session.execute(
                select(AssetModel).order_by(AssetModel.confidence_score.desc()).offset(offset).limit(limit)
            )
            models = result.scalars().all()
            return [Asset.model_validate(m) for m in models]
            
    async def count(self) -> int:
        async with async_session_maker() as session:
            result = await session.execute(select(func.count()).select_from(AssetModel))
            cnt = result.scalar()
            return cnt if cnt else 0

class JobRepository:
    async def save(self, job: CrawlJob) -> None:
        async with async_session_maker() as session:
            # We assume it has an ID, handled upstream if new
            model = await session.get(CrawlJobModel, str(job.id))
            if not model:
                model = CrawlJobModel(
                    id=str(job.id),
                    seed_urls=json.dumps(job.seed_urls),
                    target_keyword=job.target_keyword,
                    file_extension=job.file_extension,
                    max_requests=job.max_requests,
                    state=job.state.value
                )
                session.add(model)
            else:
                model.state = job.state.value
            await session.commit()
