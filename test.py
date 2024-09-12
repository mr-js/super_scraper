import asyncio
import time
from secrets import token_hex
from tasks import scrape_data


targets = [{'id': token_hex(4), 'name': f'Task {x}', 'url': 'https://example.com'} for x in range(8)]


async def fetch_data(target):
    url = target['url']
    task_id = target['id']
    task_name = target['name']
    task = scrape_data.delay(url)
    while not task.ready():
        print(f'Task #{task_id} "{task_name}" for {url} is not ready yet...')
        await asyncio.sleep(2)
    result = task.get(timeout=10)
    print(f'Result for task #{task_id} "{task_name}" with URL {url}: {result}')
    return {'id': task_id, 'id': task_name, 'result': result}


async def run_all_tasks():
    tasks = [fetch_data(target) for target in targets]
    results = await asyncio.gather(*tasks)
    print(f"All tasks completed. Results: {results}")


if __name__ == "__main__":
    asyncio.run(run_all_tasks())
