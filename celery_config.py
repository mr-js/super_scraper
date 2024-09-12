from celery import Celery
import os


os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')
app = Celery('tasks', broker='pyamqp://guest@localhost//', backend='redis://localhost')


app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


import tasks