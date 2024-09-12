from celery_config import app
import aiohttp
from lxml import html
import asyncio


@app.task
def scrape_data(url):
    return asyncio.run(fetch_data(url))


async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.text()
            tree = html.fromstring(content)
            data = next(iter(tree.xpath('//title/text()')), '')
            return data