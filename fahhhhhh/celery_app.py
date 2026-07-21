from celery import Celery
from config import settings

celery_app = Celery(
    'fahh',
    broker = f'redis://{settings.redis_host}:{settings.redis_port}/0',
    backend =f'redis://{settings.redis_host}:{settings.redis_port}/0',
    include=["scheduler"],
)
