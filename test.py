import logging
import asyncio
import time
from secrets import token_hex, choice
from tasks import scrape_data
import nodriver as uc
import json
import os, sys


class SuperScrapper:
    proxies = {}
    def __init__(self):
        logging.basicConfig(
            handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(f'{self.__class__.__name__}.log', 'w', 'utf-8')
                    ],
            format='%(asctime)s [%(funcName)s] %(levelname)s %(message)s',
            datefmt='%Y.%m.%d %H:%M:%S',
            level=logging.ERROR
            )    
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        self.log.info('STARTED')
        asyncio.run(self.load_proxies())


    async def load_proxies(self):
        try:
            url = 'https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&proxy_format=protocolipport&format=text'
            driver = await uc.start(browser_args=[f"--proxy-server=socks5://127.0.0.1:2080", '--lang=en',])
            tab = await driver.get(url)
            content = await tab.select('pre')
            self.proxies = content.text.split('\n')
            await tab.close()
            if len(self.proxies) > 0:
                self.log.info(f'proxies updated OK: {len(self.proxies)}')
            else:
                raise Exception('cannot get proxies')
        except Exception as e:
            self.log.critical(e)    


    async def fetch_data(self, target, timeout=10, precheck_proxy=False):
        url = target['url']
        task_id = target['id']
        task_name = target['name']
        for attempt in range(len(self.proxies)):
            self.log.debug(f'{len(self.proxies)=}')
            try:
                proxy = choice(self.proxies)
            except:
                break
            if precheck_proxy:
                self.log.debug(f'{target=} with {proxy=}')
                task = scrape_data.delay(url='https://api.ipify.org?format=json', proxy=proxy, timeout=timeout)
                while not task.ready():
                    await asyncio.sleep(1)
                if not task.get(timeout=timeout):
                    try:
                        self.proxies.remove(proxy)
                    except:
                        pass
                    continue
            task = scrape_data.delay(url=url, proxy=proxy, timeout=timeout)
            while not task.ready():
                await asyncio.sleep(1)
            result = task.get(timeout=timeout)
            if not result:
                try:
                    self.proxies.remove(proxy)
                except:
                    pass
                continue
            self.log.debug(f'Result for task #{task_id} "{task_name}" with URL {url}: {result}')
            break
        return {'id': task_id, 'name': task_name, 'result': result}


    async def run_all_tasks(self, targets):
        tasks = [self.fetch_data(target) for target in targets]
        results = await asyncio.gather(*tasks)
        self.log.info(f"All tasks completed: {results=}")


if __name__ == "__main__":
    ss = SuperScrapper()
    demo_targets_amount = 10
    targets = [{'id': token_hex(4), 'name': f'Task {x}', 'url': 'https://api.ipify.org?format=json'} for x in range(demo_targets_amount)]
    asyncio.run(ss.run_all_tasks(targets))
