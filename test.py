import logging
import asyncio
import time
from secrets import token_hex, choice
from tasks import check_connection, scrape_proxies, scrape_data
import json
import os, sys
from lxml import html
from tqdm.asyncio import tqdm
import codecs


class SuperScrapper:
    proxies = {}
    def __init__(self, debug=False, timeout=10, active_proxy_percent=30, precheck_proxy=False):
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
        self.log.setLevel(logging.DEBUG) if debug else self.log.setLevel(logging.INFO)
        self.log.info('STARTED')
        self.timeout = timeout
        self.active_proxy_percent = active_proxy_percent
        self.active_proxy_limit = 0
        self.precheck_proxy = precheck_proxy
        self.proxies = {}
        self.internet_check_interval = 30
        self.internet_pause_interval = 10
        self.internet_check_stop = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        asyncio.run(self.load_proxies())


    async def pause_tasks(self):
        self.log.debug(f'Pausing tasks for {self.internet_pause_interval} sec...')
        self.internet_pause_interval *= 2
        self.pause_event.clear()


    async def resume_tasks(self):
        self.log.debug('Resuming tasks...')
        self.internet_pause_interval = self.internet_check_interval
        self.pause_event.set()


    async def check_internet(self):
        while not self.internet_check_stop.is_set():
            # DEMO
            # connected = choice([True, False])
            # DEMO
            try:
                task = check_connection.delay()
                while not task.ready():
                    await asyncio.sleep(1)
                connected = task.get(timeout=self.timeout)
            except:
                connected = False
            if not connected:
                self.log.warning('Internet is down')
                await self.pause_tasks()
            else:
                await self.resume_tasks()
            await asyncio.sleep(self.internet_pause_interval)


    async def load_proxies(self):
        while True:
            task = scrape_proxies.delay()
            while not task.ready():
                await asyncio.sleep(1)
            self.proxies = task.get(timeout=self.timeout)
            self.active_proxy_count = len(self.proxies)
            self.active_proxy_limit = int(self.active_proxy_percent * self.active_proxy_count / 100)
            if self.active_proxy_count > 0:
                self.log.debug(f'proxies updated: {self.active_proxy_count}')
                self.internet_pause_interval = self.internet_check_interval
                break
            else:
                self.log.warning(f'proxies unavailable (waiting {self.internet_pause_interval} sec)')
                await asyncio.sleep(self.internet_pause_interval)
                self.internet_pause_interval *= 2


    async def fetch_data(self, target, mode):     
        task_id = target['id']
        task_name = target['name']
        task_url = target['url']
        while True:
            await self.pause_event.wait()         
            self.active_proxy_count = len(self.proxies)
            if self.active_proxy_count < self.active_proxy_limit:
                await self.load_proxies()
            self.log.debug(f'{self.active_proxy_count=}, {self.active_proxy_limit=}')
            try:
                proxy = choice(self.proxies)
                # DEMO
                # proxy = 'socks5://127.0.0.1:2080'
                # DEMO
                self.log.debug(f'selected {proxy=}')
            except:
                self.log.warning('no proxy choice (repeat selection)')
                await self.load_proxies()
            if self.precheck_proxy:
                self.log.debug(f'{target=} with {proxy=}')
                task = scrape_data.delay(url='https://api.ipify.org/?format=json', proxy=proxy, timeout=self.timeout)
                while not task.ready():
                    await asyncio.sleep(1)
                if not task.get(timeout=self.timeout):
                    try:
                        self.proxies.remove(proxy)
                    except:
                        pass
                    continue
            task = scrape_data.delay(url=task_url, mode=mode, proxy=proxy, timeout=self.timeout)
            while not task.ready():
                await asyncio.sleep(1)
            task_result = task.get(timeout=self.timeout)
            if not task_result:
                try:
                    self.proxies.remove(proxy)
                except:
                    pass
                continue
            break
        self.log.debug(f'result for task #{task_id} "{task_name}" in "{task_url}": {task_result}')
        self.pbar.update(1)
        return {'id': task_id, 'name': task_name, 'url': task_url, 'result': task_result}


    async def run_tasks(self, targets, mode, output):
        self.tasks = [asyncio.create_task(self.fetch_data(target, mode)) for target in targets]
        self.pbar = tqdm(total=len(self.tasks))
        self.results = await asyncio.gather(*self.tasks)
        self.internet_check_stop.set()
        self.pbar.close()
        self.log.info(f"FINISHED")
        with codecs.open(output, 'w', 'utf-8', errors='ignore') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=4)
        os.mkdir('output') if not os.path.exists('output') else ...
        for result in self.results:
            self.log.debug(result)
            file = result.get('id', '') + '_' + result.get('name', '') + '.html'
            filename = os.path.join('output', file)
            with codecs.open(filename, 'w', 'utf-8', errors='ignore') as f:
                f.write(result.get('result', ''))  

    
    async def run(self, targets, mode, output):
        task_runner = asyncio.create_task(self.run_tasks(targets, mode, output))
        internet_checker = asyncio.create_task(self.check_internet())
        await asyncio.gather(task_runner, internet_checker)


if __name__ == "__main__":
    demo_targets = [{'id': token_hex(4), 'name': f'Task {x}', 'url': 'https://api.ipify.org/?format=json'} for x in range(2)]
    ss = SuperScrapper(debug=False)
    asyncio.run(ss.run(targets=demo_targets, mode=1, output='results.json'))
