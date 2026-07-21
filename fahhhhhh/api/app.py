import sys,os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.db import init_db
from core.scheduler import start_scheduler
from fastapi.staticfiles import StaticFiles
from api.routes import core_route
from api.routes import watchlist_routes, report_routes, alert_routes
from core.cache import start_event_listen
from core.config import CHARTS_DIR
from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    core_route.init_graph()
    scheduler= start_scheduler()
    start_event_listen()
    yield
    scheduler.shutdown()


app=FastAPI(
    title= 'Fahhh',
    version='1.0.0',
    lifespan=lifespan
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

os.makedirs(CHARTS_DIR, exist_ok=True)
app.mount("/charts", StaticFiles(directory=CHARTS_DIR), name="charts")


app.include_router(core_route.app)
app.include_router(watchlist_routes.app)
app.include_router(report_routes.app)
app.include_router(alert_routes.app)