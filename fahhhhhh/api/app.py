from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.insert(0, "/Users/prashant/Desktop/fxis/task/fahhhhhh")
from db import init_db
from scheduler import start_scheduler

from fastapi.staticfiles import StaticFiles
from api.routes import core_route
from api.routes import watchlist_routes, report_routes, alert_routes
from contextlib import asynccontextmanager
import os



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    core_route.init_graph()
    scheduler= start_scheduler()
    yield
    scheduler.shutdown()


app=FastAPI(
    title= 'Fahhh',
    version='1.0.0',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("charts", exist_ok=True)
app.mount("/charts", StaticFiles(directory="charts"), name="charts")


app.include_router(core_route.app)
app.include_router(watchlist_routes.app)
app.include_router(report_routes.app)
app.include_router(alert_routes.app)