from fasthtml.common import Div, Form, Input, Button, H2
from src.container import container
from src.presentation.components import Layout, AssetTable
from src.infrastructure.logger import logger
from typing import Any

def setup_routes(app: Any, rt: Any) -> None:

    @rt("/")
    async def get(page: int = 1) -> Any:
        assets = await container.asset_service.get_assets(page)
        total = await container.asset_service.get_total_count()
        return Layout("Document Discovery", 
            Div(
                Form(
                    Input(name="urls", placeholder="Enter comma-separated seed URLs", cls="border p-2 w-full mb-2"),
                    Button("Start Crawl", type="submit", cls="bg-blue-600 text-white px-4 py-2 rounded"),
                    hx_post="/start", hx_target="#status"
                ),
                cls="mb-8 p-4 bg-gray-100 rounded"
            ),
            Div(id="status"),
            Div(
                H2("Passed Assets", cls="text-xl font-bold mb-4"),
                Div(f"Total passed: {total}", id="total-count", hx_get="/count", hx_trigger="every 5s"),
                AssetTable(assets, page),
                hx_get=f"/?page={page}", hx_trigger="every 10s", hx_select="#asset-table", hx_swap="outerHTML"
            )
        )

    @rt("/start", methods=["POST"])
    async def post_start(urls: str) -> Any:
        seed_urls = [u.strip() for u in urls.split(",") if u.strip()]
        if not seed_urls:
            return Div("Please enter at least one URL.", cls="text-red-500")
        job_id = await container.crawl_manager.start_crawl(seed_urls, max_requests=10) # Fixed cap for demo
        logger.info("started_crawl", job_id=job_id)
        return Div(f"Started crawl job {job_id}", cls="text-green-600 font-bold")

    @rt("/count")
    async def get_count() -> Any:
        total = await container.asset_service.get_total_count()
        return f"Total passed: {total}"
