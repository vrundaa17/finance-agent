# Finance Agent 

Finance Agent  is a full-stack market intelligence tool for NSE-listed Indian equities (and other Yahoo Finance tickers). It combines a LangGraph multi-agent pipeline, an LSTM-based price direction model, a FastAPI backend, a Streamlit dashboard, and an MCP server so the same analysis can be driven from Claude Desktop.

## What it does

- Generates a daily AI research brief per stock: fundamentals interpretation, news sentiment, risk assessment, and buy/sell target levels, compiled into one report.
- Predicts short-term price direction (up/down) using an LSTM model trained on price, volume, and technical features, with an ARIMA/statistical baseline for comparison.
- Tracks named watchlists of tickers, with scheduled report generation and price alerts.
- Logs predictions and lets a human confirm or flag the actual outcome once known, for ongoing accuracy tracking.
- Exposes everything as MCP tools, so Claude Desktop can pull fundamentals, news, charts, and reports directly.

## Architecture

```
front/   Streamlit dashboard (dashboard, stock analysis, portfolio, alerts, edit)
api/     FastAPI app — routes, watchlist storage, request schemas
agent/   LangGraph pipeline, LSTM model, target calculation, data fetching (yfinance/Finnhub)
mcp/     MCP server exposing the same capabilities as tools/resources for Claude Desktop
db.py    SQLite setup
scheduler.py   APScheduler jobs (daily reports, alert checks, cleanup, prediction verification)
visualise.py   Chart generation (price, volume, fundamentals)
```

**Report pipeline (LangGraph):** fetch fundamentals + price history -> fetch news -> data quality check -> (partial report if data is thin) -> fundamentals analysis -> risk routing (high-risk path if debt/equity, drawdown, or margin trip thresholds) -> news analysis -> risk analysis -> target calculation -> compiled report. Each stage calls Groq's `llama-3.3-70b-versatile`.

**Prediction pipeline:** engineered features (returns, moving averages, volatility, index correlation) feed an LSTM classifier; predictions are stored and later checked against actual next-day movement.

## Tech stack

FastAPI, Streamlit, LangGraph, LangChain (Groq), PyTorch, scikit-learn, statsmodels, APScheduler, SQLite, yfinance, Finnhub, MCP (FastMCP), Docker.

## Setup

**1. Environment variables** — create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_key
FINHUB_API=your_finnhub_key
NEWS_API=your_news_api_key
DB_PATH=db/watchlist.db
```

**2. Run with Docker (recommended)**

```
docker-compose up --build
```

This starts the API on `localhost:8000` and the Streamlit dashboard on `localhost:8501`.

**3. Run locally**

```
pip install -r requirements.txt
uvicorn api.app:app --reload --port 8000
streamlit run front/front.py
```

**4. MCP server (for Claude Desktop)**

Update the `sys.path.insert` at the top of `mcp/server.py` to your local project path, then point your Claude Desktop MCP config at:

```
python mcp/server.py
```

## API overview

- `GET /health` — service status
- `GET /quotes?tickers=RELIANCE.NS,TCS.NS` — live price + change
- `GET /news` — general market news
- Watchlist, report, and alert routes under `api/routes/` for CRUD on watchlists, cached reports, and price alerts

Full request/response shapes are in `api/schema.py`.

## MCP tools

`analyse_stock`, `fundamentals`, `news`, `statement`, `charts` (+ a `chart://` resource for inline images), plus watchlist and alert management (`create_watchlist`, `add_stock`, `set_price_alert`, `view_alerts`, etc.).

## Notes

- `.env`, `*.db`, and `charts/` are already git-ignored — keep it that way, and rotate any API key that was ever committed or shared.
- This project outputs financial analysis for informational purposes only; it is not financial advice.