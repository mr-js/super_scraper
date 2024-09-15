from celery_config import app
import aiohttp
from aiohttp_socks import ProxyConnector
import asyncio
import nodriver as uc
from nodriver import *


native_proxy = 'socks5://127.0.0.1:2080'
response_data = []


@app.task
def check_connection(domain='http://www.example.com', timeout=10):
    return asyncio.run(fetch_connection(domain=domain, timeout=timeout))


async def fetch_connection(domain, timeout):
    url = domain
    connector = ProxyConnector.from_url(native_proxy)
    my_timeout = aiohttp.ClientTimeout(total=timeout,  sock_connect=timeout, sock_read=timeout)
    client_args = {'trust_env' : True, 'connector' : connector, 'timeout': my_timeout}
    try:
        async with aiohttp.ClientSession(**client_args) as session:
            async with session.get(url) as response:
                    return True if response.status == 200 else False
    except Exception as e:
        return False


@app.task
def scrape_proxies():
    return asyncio.run(fetch_proxies())


async def fetch_proxies():
    proxies = {}
    url = 'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&proxy_format=protocolipport&format=text'
    driver = await uc.start(browser_args=['--lang=en', '--headless=chrome', f"--proxy-server={native_proxy}"])
    tab = None
    try:
        tab = await driver.get(url)
        content = await tab.select('pre')
        proxies = content.text.split('\n')
    except Exception as e:
        pass
    finally:
        if tab:
            await tab.close()            
        driver.stop()
        return proxies


@app.task
def scrape_data(url, mode, proxy, timeout=10):
    if mode == 0:
        return asyncio.run(fetch_data_by_request(url, proxy, timeout=timeout))
    else:
        return asyncio.run(fetch_data_by_browser(url, proxy, timeout=timeout))


async def fetch_data_by_request(url, proxy, timeout):
    data = None
    connector = ProxyConnector.from_url(proxy)
    my_timeout = aiohttp.ClientTimeout(
        total=timeout, # total timeout (time consists connection establishment for a new connection or waiting for a free connection from a pool if pool connection limits are exceeded) default value is 5 minutes, set to `None` or `0` for unlimited timeout
        sock_connect=timeout, # Maximal number of seconds for connecting to a peer for a new connection, not given from a pool. See also connect.
        sock_read=timeout # Maximal number of seconds for reading a portion of data from a peer
    )
    client_args = {'trust_env' : True, 'connector' : connector, 'timeout': my_timeout}
    try:
        response_code = 0
        async with aiohttp.ClientSession(**client_args) as session:
            async with session.get(url) as response:
                    response_code = response.status
                    # print(f'{url=} {proxy=} {timeout=} {response_code=}')
                    if response_code == 200:
                        data = await response.text()
                    else:
                        raise Exception(f'{response_code=}')
    except Exception as e:
        pass
    finally:
        return data
    

async def myhandler(event: cdp.network.ResponseReceived):
    global response_data
    response_data.append(event.response)
    # print(f'{event.response.url=}: {event.response.status=}')


async def fetch_data_by_browser(url, proxy, timeout):
    global response_data
    data = None
    driver = await uc.start(browser_args=['--lang=en', '--headless=chrome', f"--proxy-server={proxy}"])
    tab = None
    try:
            response_code = 0
            tab = await driver.get('data:,')
            tab.add_handler(cdp.network.ResponseReceived, myhandler)
            await tab.get(url)
            responses = list(filter(lambda x: url == x.url or url == x.url + r'/', response_data))
            if len(responses) > 0:
                response_code = responses[0].status
                # print(f'{url=} {proxy=} {timeout=} {response_code=}')
            if response_code == 200:
                data = await tab.get_content()
                if '--error-code-color' in data and 'error-debugging-info' in data:
                    data = None
                    raise Exception(f'-100')
            else:
                raise Exception(f'{response_code=}')
    except Exception as e:
        pass
    finally:
        if tab:
            await tab.close()
        driver.stop()
        return data
    

if __name__ == "__main__":
    print(f'{check_connection()=}')