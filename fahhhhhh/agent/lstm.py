import numpy as np
import pandas as pd
import yfinance as yf
import ta
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from agent.find import get_price_history
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')


window =10
def select_features(df, cols, target_col="target", top_n=12):
    correlations = df[cols].corrwith(df[target_col]).abs().sort_values(ascending=False)
    return correlations.head(top_n).index.tolist()

def feature(date, closes, volumes, low, high, horizon=1, index_df=None,news_df=None) -> pd.DataFrame:
    df = pd.DataFrame({"date": date, "Close": closes, "Volume": volumes, "Low": low, "High": high})

    df["return_1d"] = df["Close"].pct_change(1)
    df["return_3d"] = df["Close"].pct_change(3)
    df["return_5d"] = df["Close"].pct_change(5)
    df["return_10d"] = df["Close"].pct_change(10)

    df['ma5'] = df['Close'].rolling(5).mean()
    df['ma10'] = df['Close'].rolling(10).mean()
    df['ma20'] = df['Close'].rolling(20).mean()

    df["price_ma5"] = df["Close"] / df["ma5"]
    df["price_ma10"] = df["Close"] / df["ma10"]
    df["price_ma20"] = df["Close"] / df["ma20"]

    df['vol_5d'] = df['Close'].rolling(5).std()
    df['vol_20d'] = df['Close'].rolling(20).std()

    df["volume_change"] = df["Volume"].pct_change(1)
    df["volume_ma5"] = df["Volume"].rolling(5).mean()
    df["volume_vs_ma"] = df["Volume"] / df["volume_ma5"]

    df["RSI"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
    df["MACD"] = ta.trend.MACD(df["Close"]).macd()
    df["ADX"] = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"]).adx()
    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"]).cci()
    df["ATR"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()

    bb = ta.volatility.BollingerBands(df["Close"])
    df["return_lag2"] = df["return_1d"].shift(2)
    df["return_lag3"] = df["return_1d"].shift(3)
    df["rsi_lag1"] = df["RSI"].shift(1)
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    df["bb_width"] = bb.bollinger_wband()

    if index_df is not None:
        df = df.merge(index_df[["date", "index_return_1d"]], on="date", how="left")
        df["relative_return_1d"] = df["return_1d"] - df["index_return_1d"]

    if news_df is not None:
        df = df.merge(news_df[["date", "news_tone"]], on="date", how="left")
        df["news_tone"] = df["news_tone"].fillna(0)         
        df["news_tone_lag1"] = df["news_tone"].shift(1)  
    
    df["target"] = df["Close"].shift(-horizon) / df["Close"] - 1
    return df


def create_seq(X, y, close, window=10):
    Xs, ys, last_price = [], [], []
    for i in range(len(X) - window):
        Xs.append(X[i:i + window])
        ys.append(y[i + window])
        last_price.append(close[i + window - 1])  
    return np.array(Xs), np.array(ys), np.array(last_price)


feature_cols = ["Close", "return_1d", "return_3d", "return_5d", "return_10d",
                 "price_ma5", "price_ma10", "price_ma20",
                 "vol_5d", "vol_20d",
                 "RSI", "MACD", "ADX", "CCI", "ATR",
                 "volume_vs_ma", "bb_width", "rsi_lag1",
                 "return_lag2", "return_lag3"]


class LSTMmodel(nn.Module):
    def __init__(self, input_size, hidden_size=16, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.dropout = nn.Dropout(0.4)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.dropout(out[:, -1, :])
        return self.fc(out)

def directional_loss(pred, true, last_price, alpha=0.5):
    mse = nn.functional.mse_loss(pred, true)
    pred_dir = torch.tanh((pred - last_price) * 10)
    true_dir = torch.tanh((true - last_price) * 10)
    dir_penalty = torch.mean((pred_dir - true_dir) ** 2)
    return (1 - alpha) * mse + alpha * dir_penalty

def _train(X_seq,y_seq,lp_seq,input_size,n_seeds=3):
    val_cut = max(int(len(X_seq)*0.85),1)
    X_tr, y_tr, lp_tr = X_seq[:val_cut], y_seq[:val_cut], lp_seq[:val_cut]
    X_val, y_val, lp_val = X_seq[val_cut:], y_seq[val_cut:], lp_seq[val_cut:]
 
    models = []
    for seed in range(n_seeds):
        torch.manual_seed(seed)
        model =LSTMmodel(input_size, hidden_size=32,num_layers=2)
        optimiser = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-3)
 
        X_t = torch.FloatTensor(X_tr)
        y_t = torch.FloatTensor(y_tr).unsqueeze(1)
        lp_t = torch.FloatTensor(lp_tr).unsqueeze(1)
        loader = DataLoader(TensorDataset(X_t, y_t, lp_t), batch_size=16, shuffle=False)
 
        X_val_t = torch.FloatTensor(X_val)
        y_val_t = torch.FloatTensor(y_val).unsqueeze(1)
        lp_val_t = torch.FloatTensor(lp_val).unsqueeze(1)
 
        best_val_loss = float("inf")
        best_state = None
        patience, patience_left = 8, 8
        
        for epoch in range(20):
            model.train()
            for xb, yb, lpb in loader:
                optimiser.zero_grad()
                loss = directional_loss(model(xb), yb, lpb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimiser.step()
 
            model.eval()
            with torch.no_grad():
                val_loss = directional_loss(model(X_val_t), y_val_t, lp_val_t).item() if len(X_val) > 0 else loss.item()
 
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
                patience_left = patience
            else:
                patience_left -= 1
                if patience_left <= 0:
                    break
        if best_state is not None:
            model.load_state_dict(best_state)
        model.eval()
        models.append(model)
 
    return models



def dir_acc(df,cols,n_splits=3):
    X_raw = df[cols].values
    y_raw = df["target"].values
    close_raw = df["Close"].values
    
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    fold_accs = []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X_raw)):
        X_train_raw, X_test_raw = X_raw[train_idx], X_raw[test_idx]
        y_train_raw, y_test_raw = y_raw[train_idx], y_raw[test_idx]
        close_train, close_test = close_raw[train_idx], close_raw[test_idx]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_raw)
        X_test_scaled = scaler.transform(X_test_raw)

        y_scaler = StandardScaler()
        y_train_scaled = y_scaler.fit_transform(y_train_raw.reshape(-1, 1)).flatten()


        X_train_seq, y_train_seq, train_last_price = create_seq(X_train_scaled, y_train_scaled, close_train, window)
        X_test_seq, y_test_seq, last_known_price = create_seq(X_test_scaled, y_test_raw, close_test, window)

        train_last_price_scaled = np.zeros_like(train_last_price, dtype=float)  
        # last_known_price = close_test[window:window + len(y_test_seq)]
        
        if len(X_train_seq) < 20 or len(X_test_seq) == 0:
            continue
 
        lp_scaled = np.zeros_like(train_last_price, dtype=float)
        models = _train(X_train_seq, y_train_seq, lp_scaled, input_size=len(cols))
 
        with torch.no_grad():
            X_test_t = torch.FloatTensor(X_test_seq)
            preds = np.mean([m(X_test_t).numpy().flatten() for m in models], axis=0)
        preds_return = y_scaler.inverse_transform(preds.reshape(-1, 1)).flatten()
 
        direction_acc = (np.sign(preds_return) == np.sign(y_test_seq)).mean() * 100
        fold_accs.append(direction_acc)
 
    return round(float(np.mean(fold_accs)), 1) if fold_accs else None



def train_pred_lstm(price_history:dict,index_history=None,horizon=1):
    closes = price_history.get("close")
    volumes = price_history.get("volume")
    low = price_history.get("low")
    high = price_history.get("high")
    dates = price_history.get("dates")
    true_current_price = float(closes[-1])
    
    index_df = None
    if index_history is not None:
        index_df = pd.DataFrame({
            "date": index_history.get("dates"),
            "index_return_1d": pd.Series(index_history.get("close")).pct_change(1),
        })
        
    df = feature(dates, closes, volumes, low, high, horizon, index_df)
    cols = feature_cols.copy()
    if 'relative_return_1d' in df.columns:
        cols.append('relative_return_1d')
    cols = select_features(df,cols) 
    df = df.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
 
    if len(df) < window + 40:
        raise ValueError("Not enough history for a reliable LSTM forecast.")
        
    backtest_acc = dir_acc(df, cols)
    
    X_all = df[cols].values
    y_all = df["target"].values
    close_all = df["Close"].values
 
    scaler = StandardScaler().fit(X_all)
    X_scaled = scaler.transform(X_all)
    y_scaler = StandardScaler().fit(y_all.reshape(-1, 1))
    y_scaled = y_scaler.transform(y_all.reshape(-1, 1)).flatten() 
 
    X_seq, y_seq, last_price_seq = create_seq(X_scaled, y_scaled, close_all)
    lp_scaled = np.zeros_like(last_price_seq, dtype=float)
 
    models = _train(X_seq, y_seq, lp_scaled, input_size=len(cols))

    latest_X = torch.FloatTensor(X_scaled[-window:]).unsqueeze(0)
    with torch.no_grad():
        seed_preds = [m(latest_X).item() for m in models]
    pred_scaled = float(np.mean(seed_preds))
    pred_return = float(y_scaler.inverse_transform([[pred_scaled]])[0][0])
 
    current_price = float(close_all[-1])
    predicted_price = round(true_current_price * (1 + pred_return), 2)
    direction = "UP" if pred_return > 0 else "DOWN"
      
    seed_directions = [1 if p > 0 else -1 for p in seed_preds]
    agreement = seed_directions.count(seed_directions[0]) / len(seed_directions)
    confidence = round(agreement * 100, 1)
 
    return {
        "direction": direction,
        "predicted_return_pct": round(pred_return * 100, 2),
        "current_price": true_current_price,
        "predicted_price": predicted_price,
        "confidence": confidence,
        "bd_accuracy": backtest_acc,
        "horizon_days": horizon,
        "disclaimer": "ML prediction only. Not financial advice."
    }

if __name__ == "__main__":
    hist = get_price_history("RELIANCE.NS", "3y")
    index_hist = get_price_history("^NSEI", "3y")
    result = train_pred_lstm(hist, index_hist)
    for i in (1,5,21):
        result = train_pred_lstm(hist, index_hist, horizon=i)
        print(f"\nHorizon : {i}")
        for k, v in result.items():
            print(k, ":", v)
    
    
    
    
    
    
    
    
    
    
# def lstm_walk(sname, period="3y", horizons=(1, 5, 21)):
#     hist = get_price_history(sname, period)
#     index_hist = get_price_history("^NSEI", period)
#     index_df = pd.DataFrame({
#         "date": index_hist["dates"],
#         "index_return_1d": pd.Series(index_hist['close']).pct_change(1),
#     })

#     horizon_labels = {1: "1-day", 5: "5-day (weekly)", 21: "21-day (~monthly)"}

#     for horizon in horizons:
#         print(horizon)
#         results = run_horizon(sname, horizon, hist, index_df)
#         for r in results:
#             print(f"fold {r['fold']}: test_mse={r['test_mse']:.2f}  naive_mse={r['naive_mse']:.2f}  "
#                   f"direction_acc={r['direction_acc']:.1f}%")

#         avg_direction = np.mean([r["direction_acc"] for r in results])
        
#         print(f"LSTM direction_acc: {avg_direction:.1f}% ")    