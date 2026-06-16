import os
import aiohttp
from src.config import config
from src.infrastructure.logger import logger

class DownloadManager:
    def __init__(self) -> None:
        self.download_dir = config.download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    async def stream_download(self, url: str, filename: str) -> str:
        filepath = os.path.join(self.download_dir, filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                with open(filepath, 'wb') as fd:
                    async for chunk in response.content.iter_chunked(1024 * 8):
                        fd.write(chunk)
        
        logger.info("asset_downloaded", url=url, filepath=filepath)
        return filepath
