from celery_config import app
import aiohttp
from lxml import html
from secrets import token_hex, choice
import asyncio


@app.task
def scrape_data(url, proxies):
    return asyncio.run(fetch_data(url, proxies))


async def fetch_data(url, proxies):
    data = ''
    my_timeout = aiohttp.ClientTimeout(
        total=10, # total timeout (time consists connection establishment for a new connection or waiting for a free connection from a pool if pool connection limits are exceeded) default value is 5 minutes, set to `None` or `0` for unlimited timeout
        sock_connect=10, # Maximal number of seconds for connecting to a peer for a new connection, not given from a pool. See also connect.
        sock_read=10 # Maximal number of seconds for reading a portion of data from a peer
    )

    client_args = dict(
        trust_env=True,
        timeout=my_timeout
    )
    for attempt in range(len(proxies)):
        try:
            async with aiohttp.ClientSession(**client_args) as session:
                async with session.get(url, proxy=choice(proxies)) as response:
                        if response.status == 200:
                            content = await response.text()
                            # tree = html.fromstring(content)
                            # data = next(iter(tree.xpath('//body/text()')), '')
                            data = content
                            break
                        else:
                            raise Exception(f'Status code {response.status}')
        except Exception as e:
            continue
    return data