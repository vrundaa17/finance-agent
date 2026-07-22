import redis,hashlib
from core.config import settings
# import threading
import logging
logger = logging.getLogger(__name__)
r = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

    
def cached_llm_call(stage, llm, prompt):
    key = f"llm-{stage}:{hashlib.sha256(prompt.encode()).hexdigest()}"
    cached = r.get(key)
    if cached:
        logger.info(f"[Cache HIT] {stage}")
        return cached
    logger.info(f"[Cache MISS] {stage}")
    response = llm.invoke(prompt)
    r.set(key, response.content, ex=1800)
    return response.content

def check_ratelimit(source,limit,window):
    key = f"ratelimit:{source}"
    current = r.incr(key)
    if current == 1:
        r.expire(key, window)
    return current <= limit


def set_job_state(job_id,status):
    r.set(f"job:{job_id}",status,ex=3600)

def get_job_state(job_id):
    return r.get(f"job:{job_id}")

# def start_event_listen():
#     def listen():
#         pubsub = r.pubsub()
#         pubsub.subscribe('reports')
#         for message in pubsub.listen():
#             if message["type"]=='message':
#                 logger.info(f"Got your message: {message['data']}")
#     thread= threading.Thread(target=listen,name='listen_pubsub',daemon=True)
#     thread.start()