from celery_config import app
import aiohttp
import asyncio


@app.task
def scrape_data(url, proxy, timeout=10):
    return asyncio.run(fetch_data(url, proxy, timeout=timeout))


async def fetch_data(url, proxy, timeout):
    data = None
    my_timeout = aiohttp.ClientTimeout(
        total=timeout, # total timeout (time consists connection establishment for a new connection or waiting for a free connection from a pool if pool connection limits are exceeded) default value is 5 minutes, set to `None` or `0` for unlimited timeout
        sock_connect=timeout, # Maximal number of seconds for connecting to a peer for a new connection, not given from a pool. See also connect.
        sock_read=timeout # Maximal number of seconds for reading a portion of data from a peer
    )

    client_args = dict(
        trust_env=True,
        timeout=my_timeout
    )
    try:
        async with aiohttp.ClientSession(**client_args) as session:
            async with session.get(url, proxy=proxy) as response:
                    if response.status == 200:
                        data = await response.text()
                    else:
                        raise Exception(f'Status code {response.status}')
    except Exception as e:
        pass
    finally:
        return data