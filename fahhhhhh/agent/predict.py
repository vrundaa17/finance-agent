import numpy as np
import pandas as pd
import yfinance as yf
import ta
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

def feature(closes,volumes,low,high)->pd.DataFrame:
    df = pd.DataFrame({"Close": closes, "Volume": volumes, "Low":low, "High":high })
    
    df["return_1d"]  = df["Close"].pct_change(1)
    df["return_3d"]  = df["Close"].pct_change(3)
    df["return_5d"]  = df["Close"].pct_change(5)
    df["return_10d"] = df["Close"].pct_change(10)
    
    df['ma5'] = df['Close'].rolling(5).mean()
    df['ma10'] = df['Close'].rolling(10).mean()
    df['ma20'] = df['Close'].rolling(20).mean()
    
    df["price_ma5"]  = df["Close"] / df["ma5"]
    df["price_ma10"]  = df["Close"] / df["ma10"]
    df["price_ma20"]  = df["Close"] / df["ma20"]
    
    df['vol_5d'] = df['Close'].rolling(5).std()
    df['vol_20d'] = df['Close'].rolling(20).std()
    
    df["volume_change"]= df["Volume"].pct_change(1)
    df["volume_ma5"]= df["Volume"].rolling(5).mean()
    df["volume_vs_ma"]= df["Volume"] / df["volume_ma5"]
    
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
    df["MACD"] = ta.trend.MACD(df["Close"]).macd()
    df["ADX"] = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"]).adx()

    df["CCI"] = ta.trend.CCIIndicator(df["High"], df["Low"], df["Close"]).cci()

    df["ATR"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()

    bb = ta.volatility.BollingerBands(df["Close"])
    df["return_lag1"] = df["return_1d"].shift(1)
    df["return_lag2"] = df["return_1d"].shift(2)
    df["return_lag3"] = df["return_1d"].shift(3)

    df["rsi_lag1"] = df["RSI"].shift(1)
    df["bb_high"] = bb.bollinger_hband()
    df["bb_low"] = bb.bollinger_lband()
    df["bb_width"] = bb.bollinger_wband()
    
    future_return = df["Close"].shift(-1) / df["Close"] - 1

    df["target"] = (future_return > 0.005).astype(int)
    return df


def train_pred(price_history:dict):
    closes = price_history.get("close")
    volumes = price_history.get("volume")
    low = price_history.get("low")
    high = price_history.get("high")
    # closes =hist['Close']
    # volumes = hist['Volume']
    # low = hist['Low']
    # high = hist['High']
    
    df = feature(closes,volumes,low,high)
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    
    
    X = df.drop(columns=["target", "Close", "High", "Low"])
    y = df["target"]    
    feature_cols = X.columns.tolist()
     
    split = int(len(X) * 0.8)
    X_train = X.iloc[:split]
    X_test = X.iloc[ split:]
    y_train = y.iloc[:split]
    y_test = y.iloc[ split:]
    
    model = XGBClassifier(n_estimators=300,max_depth=4,learning_rate=0.01,
        subsample=0.5,colsample_bytree=0.5,random_state=42,eval_metric="logloss")
    model.fit(X_train,y_train)
        
    prob = model.predict_proba(X_test)[:,1]
    y_pred = (prob > 0.6).astype(int) 
        
    accuracy = round(accuracy_score(y_test,y_pred)*100,2)

    latest = X.iloc[-1].values.reshape(1, -1)
    prediction= int(model.predict(latest)[0])
    confidence = round(max(model.predict_proba(latest)[0]) * 100)
    direction= "UP" if prediction == 1 else "DOWN"
    importances = dict(zip(feature_cols, model.feature_importances_))
    top_features = sorted(importances.items(),key=lambda x: x[1],reverse=True)[:5]
    
    return {
    "direction": str(direction),
    "confidence": float(confidence),
    "accuracy": float(accuracy),
    "current_price": float(closes[-1]),
    "top_signals": [
        {
            "feature": str(k),
            "importance": float(round(v, 3))
        }
        for k, v in top_features
    ],
    "training_days": int(split),
    "test_days": int(len(X_test)),
    "disclaimer": "ML prediction only. Not financial advice. Backtest accuracy does not guarantee future results."
}
    
# if __name__=="__main__":
#     stock= yf.Ticker("TATAPOWER.NS")
#     # hist = stock.history(period="3y")
#     from find import get_price_history
#     hist = get_price_history("TATAPOWER.NS","3y")
#     result =train_pred(hist)
#     for k, v in result.items():
#         print(k, type(v))