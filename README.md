# Finance Agent 

AI-powered market intelligence for NSE-listed Indian equities (and any Yahoo Finance ticker). A LangGraph pipeline generates daily research briefs, an LSTM model forecasts short-term price direction, and everything is reachable through a FastAPI backend, a Streamlit dashboard, and an MCP server for Claude Desktop.

## Features

- **Daily AI brief** — fundamentals, news sentiment, risk assessment, and buy/sell targets compiled into one report
- **LSTM price direction forecasting** — ensemble model with walk-forward CV backtesting (~50-55% direction accuracy, documented as a known ceiling, not actively chased further)
- **Watchlists & alerts** — track tickers, get notified on price thresholds
- **Prediction tracking** — logs every forecast and lets you confirm the actual outcome later
- **MCP integration** — every capability is also exposed as a Claude Desktop tool, backed by the same FastAPI routes (no duplicated logic)

## Stack

FastAPI · Streamlit · LangGraph · LangChain (Groq) · PyTorch · scikit-learn · Celery · Redis · SQLite · yfinance · Finnhub · MCP

## Architecture

```
front/  Streamlit dashboard
api/    FastAPI routes, schemas, DB access
agent/  LangGraph pipeline, LSTM model, target calculation, data fetching
core/   Config, DB, Redis cache, Celery, scheduler, charts
mcp/    MCP server exposing the same capabilities as tools/resources for Claude Desktop
```
## Setup

**1. Configure environment**

```bash
cp .env.example .env   # fill in your keys
```

**2. Run with Docker**

```bash
docker compose up --build
```

Starts Redis, the API (`:8000`), a Celery worker, and the dashboard (`:8501`).

**3. Run locally**

```bash
pip install -r requirements.txt
uvicorn api.app:app --reload --port 8000
celery -A core.celery_app worker --loglevel=info   # separate terminal
streamlit run front/front.py                        # separate terminal
```

**4. MCP (Claude Desktop)**

Start the API first, then point your Claude Desktop config at:

```bash
python mcp/server.py
```

## API

| Endpoint | Description |
|---|---|
| `GET /health` | API, Redis, DB, Celery status |
| `GET /quotes?tickers=...` | Live price + change |
| `GET /fundamentals/{stock}` | Price, P/E, EPS, margins, sector |
| `GET /news/{stock}` | Recent news |
| `GET /statement/{stock}` | Financial statements |
| `GET /target/{stock}` | Buy/sell/stop-loss levels |
| `GET /predict/{stock}` | LSTM direction forecast (1hr cache) |
| `/watchlists`, `/alerts`, `/report`, `/predictions` | Full CRUD — see `api/schema.py` |

## Known limitations

- No auth — fine for local use, not for public deployment
- LSTM retrains per request, not persisted to disk
- Direction accuracy is close to a coin flip — treated as an honest finding, not a bug

## Notes

`.env` and `*.db` are git-ignored — never share `.env` as-is, rotate any key that leaves this machine. This project is informational only, not financial advice.