# super_scraper
 Python Scraping with LXML Celery Rabbit Redis

 ## Usage

 ```bash
 docker-compose up -d
 docker ps
 celery -A celery_config worker --loglevel=info --pool=processes
 ```

 ## Remarks
 > [!WARNING]
 > Add for OS Windows before app initializing:
 ```python
 os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')
 ```
