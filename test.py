import asyncio
import time
from secrets import token_hex, choice
from tasks import scrape_data
import nodriver as uc
import json


targets = [{'id': token_hex(4), 'name': f'Task {x}', 'url': 'https://api.ipify.org?format=json'} for x in range(8)]

async def get_proxies():
    url = 'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&proxy_format=protocolipport&format=text'
    driver = await uc.start(browser_args=[f"--proxy-server=socks5://127.0.0.1:2080", '--lang=en',])
    tab = await driver.get(url)
    content = await tab.select('pre')
    proxies = content.text.split('\n')
    await tab.close()
    return proxies

proxies = asyncio.run(get_proxies())
# print(proxies)

async def fetch_data(target):
    url = target['url']
    task_id = target['id']
    task_name = target['name']
    task = scrape_data.delay(url=url, proxies=proxies)
    while not task.ready():
        await asyncio.sleep(1)
    result = task.get(timeout=10)
    print(f'Result for task #{task_id} "{task_name}" with URL {url}: {result}')
    return {'id': task_id, 'id': task_name, 'result': result}


async def run_all_tasks():
    tasks = [fetch_data(target) for target in targets]
    results = await asyncio.gather(*tasks)
    print(f"All tasks completed. Results: {results}")


if __name__ == "__main__":
    asyncio.run(run_all_tasks())
