from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, Boolean
from src.config import config

engine = create_async_engine(config.database_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base() # use standard declarative_base

class CrawlJobModel(Base):
    __tablename__ = "crawl_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    seed_urls: Mapped[str] = mapped_column(String)
    target_keyword: Mapped[str] = mapped_column(String)
    file_extension: Mapped[str] = mapped_column(String)
    max_requests: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String)

class AssetModel(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    content_snippet: Mapped[str] = mapped_column(String)
    confidence_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="Pending")
    local_path: Mapped[str] = mapped_column(String, nullable=True)

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
