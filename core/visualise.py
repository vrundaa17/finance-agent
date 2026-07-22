import os
import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from core.config import CHARTS_DIR
import logging
logger = logging.getLogger(__name__)

OUTPUT_DIR = CHARTS_DIR


def _parse_dates(date_string)-> list[datetime]:
    return [datetime.strptime(d,"%Y-%m-%d") for d in date_string]

def _moving_averages(values, window):
    result=[]
    for i in range(len(values)):
        if i<window-1:
            result.append(None)
        else:
            result.append(round(sum(values[i - window + 1:i + 1]) / window, 2))
    return result

def plot_price_history(price_history,ticker):
    
    dates = _parse_dates(price_history['dates'])
    closes = price_history['close']
    ma20 = _moving_averages(closes,20)
    ma50 = _moving_averages(closes,50)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(dates, closes,color="#1a2624", linewidth=1.8, label='Close Price')
    
    ma20_dates = [d for d,v in zip(dates,ma20) if v is not None]
    ma20_vals=[v for v in ma20 if v is not None]
    ma50_dates=[d for d,v in zip(dates,ma50) if v is not None]
    ma50_vals= [v for v in ma50 if v is not None ]
    
    if ma20_vals:
        ax.plot(ma20_dates, ma20_vals,linewidth=1.2,linestyle='--')
    if ma50_vals:
        ax.plot(ma50_dates, ma50_vals,linewidth=1.2,linestyle='--')
        
    ax.fill_between(dates,closes,alpha=0.08)
    ax.set_title(f"{ticker} — Price History", color="white", fontsize=14, pad=12)
    ax.set_ylabel("Price", color="#9ca3af")
    ax.tick_params(colors="#9ca3af")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=35)
 
    for spine in ax.spines.values():
        spine.set_edgecolor("#1f2937")
    ax.grid(axis="y", color="#1f2937", linewidth=0.8)
    ax.legend(facecolor="#1a1f2e", labelcolor="white", fontsize=9)
 
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f"{ticker}_price.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return path


def plot_volume(price_history,ticker):
    dates = _parse_dates(price_history["dates"])
    volumes = price_history["volume"]
    closes = price_history["close"]
    opens = price_history["open"]
 
    # green if close > open (up day), red if not
    colors = ["#22c55e" if c >= o else "#ef4444"
              for c, o in zip(closes, opens)]
 
    fig, ax = plt.subplots(figsize=(12, 3))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")
 
    ax.bar(dates, volumes, color=colors, alpha=0.75, width=1.2)
 
    ax.set_title(f"{ticker} — Volume", color="white", fontsize=14, pad=12)
    ax.set_ylabel("Volume", color="#9ca3af")
    ax.tick_params(colors="#9ca3af")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=35)
 
    for spine in ax.spines.values():
        spine.set_edgecolor("#1f2937")
 
    ax.grid(axis="y", color="#1f2937", linewidth=0.8)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K")
    )
 
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f"{ticker}_volume.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return path


def plot_fundamentals_snapshot(fundamentals: dict, ticker: str) -> str:
    metrics = {
        "P/E Ratio": fundamentals.get("pe_ratio"),
        "Forward P/E": fundamentals.get("forward_pe"),
        "EPS": fundamentals.get("eps"),
        "Profit Margin %": round(fundamentals.get("profit_margin", 0) * 100, 2)
                           if fundamentals.get("profit_margin") else None,
        "Revenue Growth %": round(fundamentals.get("revenue_growth", 0) * 100, 2)
                            if fundamentals.get("revenue_growth") else None,
        "Debt/Equity": fundamentals.get("debt_to_equity"),
    }
 

    metrics = {k: v for k, v in metrics.items() if v is not None}
 
    if not metrics:
        return None
 
    labels = list(metrics.keys())
    values = list(metrics.values())
 
    #green for positive red for more loss
    colors = []
    for label, val in zip(labels, values):
        if "Debt" in label:
            colors.append("#ef4444" if val > 100 else "#22c55e")
        elif val >= 0:
            colors.append("#00d4aa")
        else:
            colors.append("#ef4444")
 
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#0f1117")
 
    bars = ax.barh(labels, values, color=colors, alpha=0.85, height=0.5)
 
    #value titles
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + abs(max(values)) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.2f}",
            va="center", color="white", fontsize=9
        )
 
    ax.set_title(f"{ticker} — Key Metrics Snapshot", color="white", fontsize=14, pad=12)
    ax.tick_params(colors="#9ca3af")
    ax.set_xlabel("Value", color="#9ca3af")
 
    for spine in ax.spines.values():
        spine.set_edgecolor("#1f2937")
 
    ax.grid(axis="x", color="#1f2937", linewidth=0.8)
    ax.axvline(0, color="#4b5563", linewidth=0.8)
 
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, f"{ticker}_fundamentals.png")
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    return path
 
 
def generate_all_charts(chart_types: list[str],price_history: dict, fundamentals: dict, ticker: str) -> dict:
    paths = {}
    logger.info("chart_types: ",chart_types)
    if "price" in chart_types:
        try:
            paths["price"] = plot_price_history(price_history, ticker)
        except Exception as e:
            paths["price"] = None
            logger.error(f"price chart failed: {e}")
    if "volume" in chart_types:
        try:
            paths["volume"] = plot_volume(price_history, ticker)
        except Exception as e:
            paths["volume"] = None
            logger.error(f"volume chart failed: {e}")
            
    if "fundamentals" in chart_types:
        try:
            paths["fundamentals"] = plot_fundamentals_snapshot(fundamentals, ticker)
        except Exception as e:
            paths["fundamentals"] = None
            logger.error(f"fundamentals chart failed: {e}")
 
    return paths




def clear_all_charts():
    if not os.path.isdir(OUTPUT_DIR):
        return 0
    deleted = 0
    for filename in os.listdir(OUTPUT_DIR):
        filepath = os.path.join(OUTPUT_DIR, filename)
        if os.path.isfile(filepath):
            try:
                os.remove(filepath)
                deleted += 1
            except OSError as e:
                logger.error(f"Could not delete {filepath}: {e}")
    return deleted
        
# if __name__ =="__main__":
#     from find import get_price_history,get_kyc_of_stock
#     price_history = get_price_history('CIPLA.NS',period='1y')
#     kyc_data= get_kyc_of_stock('CIPLA.NS')
#     paths = generate_all_charts(price_history, kyc_data, "CIPLA.NS")
#     for name, path in paths.items():
#         logger.info(f"  {name}: {path}")