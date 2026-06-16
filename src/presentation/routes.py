from fasthtml.common import Div, Form, Input, Button, H2, Textarea, Select, Option, P, Li, Ul, Tr, Td, A
from src.container import container
from src.presentation.components import Layout, AssetTable
from src.infrastructure.logger import logger
from typing import Any
from starlette.responses import HTMLResponse  # <-- ADD THIS LINE

def setup_routes(app: Any, rt: Any) -> None:

    @rt("/")
    async def get(page: int = 1) -> Any:
        import traceback
        try:
            assets = await container.asset_service.get_assets(page)
            print(f"DEBUG assets: type={type(assets)}, len={len(assets)}")
            total = await container.asset_service.get_total_count()
            print(f"DEBUG total: type={type(total)}, value={total!r}")
        
            # Build piece by piece to isolate the bool
            table = AssetTable(assets, page)
            print(f"DEBUG table built OK: {type(table)}")
        
            content = Layout("Targeted Harvester",
                Div("FORM PLACEHOLDER"),   # strip the form out temporarily
                Div(id="status"),
                Div("INFO PLACEHOLDER"),   # strip the info box out temporarily
                Div(
                    H2("High Confidence Assets", cls="text-xl font-bold mb-4"),
                    Div(f"Total passed: {total}", id="total-count", hx_get="/count", hx_trigger="every 5s"),
                    table,
                    hx_get=f"/?page={page}", hx_trigger="every 10s", hx_select="#asset-table", hx_swap="outerHTML"
                )
            )
            print("DEBUG content built OK")
            return content
        except Exception as e:
            print(f"DEBUG EXCEPTION: {e}")
            traceback.print_exc()
            raise

        content = Layout("Targeted Harvester",   # <-- Store in variable
            Div(
                Form(
                    Div(
                        Textarea(name="urls", placeholder="Enter comma or newline separated seed URLs", cls="border p-2 w-full mb-2 h-32"),
                        cls="mb-4"
                    ),
                    Div(
                        Input(name="target_keyword", placeholder="Mandatory Target Keyword", required=True, cls="border p-2 w-full mb-2"),
                        cls="mb-4"
                    ),
                    Div(
                        Select(
                            Option("PDF", value="pdf"),
                            Option("DOC", value="doc"),
                            Option("DOCX", value="docx"),
                            Option("EPUB", value="epub"),
                            Option("TXT", value="txt"),
                            Option("XLSX", value="xlsx"),
                            name="file_extension",
                            cls="border p-2 w-full mb-4"
                        ),
                        cls="mb-4"
                    ),
                    Button("Start Harvester", type="submit", cls="bg-blue-600 text-white px-4 py-2 rounded"),
                    hx_post="/start", hx_target="#status"
                ),
                cls="mb-8 p-4 bg-gray-100 rounded shadow"
            ),
            Div(id="status"),
            Div(
                H2("Confidence Score Logic", cls="text-lg font-bold mb-2"),
                P("The Confidence Score is an aggregation of:", cls="mb-2 text-sm text-gray-700"),
                Ul(
                    Li("1. Header / Extension Check (Is the file type correct?)", cls="ml-4 list-disc text-sm text-gray-700"),
                    Li("2. Keyword Density (Does the target keyword appear in text snippet?) [Weight: 0.7]", cls="ml-4 list-disc text-sm text-gray-700"),
                    Li("3. URL Relevance (Does the URL path contain the target keyword?) [Weight: 0.15]", cls="ml-4 list-disc text-sm text-gray-700"),
                    cls="mb-6"
                ),
                cls="mb-4 p-4 bg-blue-50 border border-blue-200 rounded"
            ),
            Div(
                H2("High Confidence Assets", cls="text-xl font-bold mb-4"),
                Div(f"Total passed: {total}", id="total-count", hx_get="/count", hx_trigger="every 5s"),
                AssetTable(assets, page),
                hx_get=f"/?page={page}", hx_trigger="every 10s", hx_select="#asset-table", hx_swap="outerHTML"
            )
        )
        return HTMLResponse(str(content))  # <-- RETURN THIS INSTEAD

    # ... rest of file stays EXACTLY the same ...

    @rt("/start", methods=["POST"])
    async def post_start(urls: str = "", target_keyword: str = "", file_extension: str = "pdf") -> Any:
        # Support newline or comma separation
        raw_urls = urls.replace("\n", ",").split(",")
        seed_urls = [u.strip() for u in raw_urls if u.strip()]
        
        if not seed_urls:
            return Div("Please enter at least one URL.", cls="text-red-500 font-medium")
            
        normalized_urls = []
        for url in seed_urls:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            normalized_urls.append(url)
            
        if not target_keyword.strip():
            return Div("Target Keyword is completely mandatory.", cls="text-red-500 font-medium")
            
        from src.application.download_service import DownloadService # Ensures download binding context
        
        job_id = await container.crawl_manager.start_crawl(
            seed_urls=normalized_urls, 
            target_keyword=target_keyword.strip(), 
            file_extension=file_extension,
            max_requests=10
        )
        logger.info("started_crawl", job_id=job_id)
        return Div(f"Started targeted harvesting job {job_id}", cls="text-green-600 font-bold")

    @rt("/count")
    async def get_count() -> Any:
        total = await container.asset_service.get_total_count()
        return f"Total passed: {total}"

    @rt("/download/{asset_id}", methods=["POST"])
    async def post_download(asset_id: str) -> Any:
        # Import injected DownloadService to execute download
        from src.application.download_service import DownloadService
        from src.infrastructure.download_manager import DownloadManager
        
        # Instantiate service to handle download logic inline for this request
        dl_service = DownloadService(DownloadManager(), container.asset_repo)
        
        try:
            filepath = await dl_service.execute_download(asset_id)
            logger.info("asset_download_successful", asset_id=asset_id, filepath=filepath)
            
            # Fetch updated asset to render new row
            asset = await container.asset_repo.get_by_id(asset_id)
            if asset:
                return Tr(
                    Td(asset.title, cls="p-2 border"),
                    Td(A(asset.url, href=asset.url, target="_blank", cls="text-blue-500"), cls="p-2 border"),
                    Td(f"{asset.confidence_score:.2f}", cls="p-2 border"),
                    Td("Ingested ✓", cls="p-2 border text-green-600 font-bold")
                )
        except Exception as e:
            logger.error("asset_download_failed", asset_id=asset_id, error=str(e))
        
        # Fallback empty string if fails
        return ""
