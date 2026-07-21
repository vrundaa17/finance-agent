from celery import Celery
from core.config import settings

celery_app = Celery(
    'fahh',
    broker = f'redis://{settings.redis_host}:{settings.redis_port}/0',
    backend =f'redis://{settings.redis_host}:{settings.redis_port}/0',
    include=["core.scheduler"],
)


def check_celery_health():
    try:
        inspector = celery_app.control.inspect(timeout=2)
        active_workers = inspector.ping()
        return bool(active_workers)  
    except Exception:
        return False