import numpy as np
import pandas as pd
import yfinance as yf
import ta
from agent.find import get_price_history
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score,precision_score,recall_score
import warnings
warnings.filterwarnings('ignore')


def feature(date,closes,volumes,low,high,index_df=None,news_df=None)->pd.DataFrame:
    df = pd.DataFrame({'date':date,"Close": closes, "Volume": volumes, "Low":low, "High":high })
    
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
    # df["return_lag1"] = df["return_1d"].shift(1)
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
    future_return = df["Close"].shift(-5) / df["Close"] - 1
    df["target"] = (future_return > 0.005).astype(int)
    return df


def train_pred(price_history:dict):
    
    closes = price_history.get("close")
    volumes = price_history.get("volume")
    low = price_history.get("low")
    high = price_history.get("high")
    date = price_history.get("dates")
    # closes =hist['Close']
    # volumes = hist['Volume']
    # low = hist['Low']
    # high = hist['High']
    
    index_hist = get_price_history("^NSEI", period="3y")
    index_df = pd.DataFrame({
        "date": index_hist["dates"],
        "index_return_1d": pd.Series(index_hist["close"]).pct_change(1),
    })
    df = feature(date,closes,volumes,low,high,index_df)
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    
    feature_cols = ["return_1d", "return_5d", "return_10d", "price_ma20","ATR", "RSI","MACD", "volume_vs_ma", "bb_width"]
    X = df[feature_cols]
    # X = df.drop(columns=["target", "Close", "High", "Low"])
    y = df["target"]    
    feature_cols = X.columns.tolist()
     
    split = int(len(X) * 0.8)
    X_train = X.iloc[:split]
    X_test = X.iloc[ split:]
    y_train = y.iloc[:split]
    y_test = y.iloc[ split:]
    
    model = XGBClassifier(n_estimators=100,max_depth=2,learning_rate=0.01,
        subsample=0.5,colsample_bytree=0.5,random_state=42,eval_metric="logloss",
        reg_alpha=1.0,reg_lambda=2.0)
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
    
def val(sname, period="3y", n_splits=3):
    hist =get_price_history(sname, period)
    df = feature(hist["close"], hist["volume"], hist["low"], hist["high"])
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    feature_cols = ["return_1d", "return_5d", "return_10d", "price_ma20", "ATR", "RSI", "MACD", "volume_vs_ma", "bb_width"]
    X = df[feature_cols]
    y = df["target"]
    tscv = TimeSeriesSplit(n_splits=n_splits)
    # train_idx,test_idx = tscv.split(X)

    results = []
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        neg = (y_train == 0).sum()
        pos = (y_train == 1).sum() 
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
        model.fit(X_train_scaled, y_train)
        # model = XGBClassifier( 
        #     n_estimators=300, max_depth=4, learning_rate=0.01, 
        #     subsample=0.5, colsample_bytree=0.5,
        #     random_state=42, eval_metric="logloss"
        # )
        # model.fit(X_train, y_train)
        preds = model.predict(X_test)
        print(f"predicted class counts: {pd.Series(preds).value_counts().to_dict()}")
        train_preds = model.predict(X_train)
        test_preds = model.predict(X_test)

        train_acc = round(accuracy_score(y_train, train_preds) * 100, 1)
        test_acc = round(accuracy_score(y_test, test_preds) * 100, 1)
        baseline = round(max(y_test.mean(), 1 - y_test.mean()) * 100, 1)


        # preds = model.predict(X_test)
        # acc = round(accuracy_score(y_test, preds) * 100, 1)
        # baseline = round(max(y_test.mean(), 1 - y_test.mean()) * 100, 1)
        # prec_down = round(precision_score(y_test,preds,pos_label=0,zero_division=0) *100,1)
        # rec_down = round(recall_score(y_test,preds,pos_label=0,zero_division=0)*100,1)
        
        print(f"fold {fold+1}: train={len(X_train)} test={len(X_test)}  "
              f"train_acc={train_acc}%  test_acc={test_acc}%  baseline={baseline}%  "
              f"gap={round(train_acc - test_acc, 1)}")


        # results.append({"fold": fold+1, "baseline": baseline, "model": acc,"down_precision": prec_down, "down_recall": rec_down})

    # return results

if __name__ == "__main__":
    val("RELIANCE.NS")
#     stock= yf.Ticker("TATAPOWER.NS")
#     # hist = stock.history(period="3y")
#     from find import get_price_history
#     hist = get_price_history("TATAPOWER.NS","3y")
#     result =train_pred(hist)
#     for k, v in result.items():
#         print(k, type(v))

# def walk_forward_validate(sname, period="3y", n_splits=3):
#     hist = get_price_history(sname, period)
#     df = feature(hist["close"], hist["volume"], hist["low"], hist["high"])
#     df = df.replace([np.inf, -np.inf], np.nan).dropna()

#     X = df.drop(columns=["target", "Close", "High", "Low"])
#     y = df["target"]

#     tscv = TimeSeriesSplit(n_splits=n_splits)
#     for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
#         X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
#         y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

#         neg = (y_train == 0).sum()
#         pos = (y_train == 1).sum()
#         scale_pos_weight = neg / max(pos, 1)

#         model = XGBClassifier(
#             n_estimators=300, max_depth=4, learning_rate=0.01,
#             subsample=0.5, colsample_bytree=0.5,
#             scale_pos_weight=scale_pos_weight,
#             random_state=42, eval_metric="logloss"
#         )
#         model.fit(X_train, y_train)

#         train_preds = model.predict(X_train)
#         test_preds = model.predict(X_test)

#         train_acc = round(accuracy_score(y_train, train_preds) * 100, 1)
#         test_acc = round(accuracy_score(y_test, test_preds) * 100, 1)
#         baseline = round(max(y_test.mean(), 1 - y_test.mean()) * 100, 1)

#         print(f"fold {fold+1}: train={len(X_train)} test={len(X_test)}  "
#               f"train_acc={train_acc}%  test_acc={test_acc}%  baseline={baseline}%  "
#               f"gap={round(train_acc - test_acc, 1)}pts")


# predicted class counts: {1: 143, 0: 35}
# fold 1: train=178 test=178  train_acc=51.1%  test_acc=55.6%  baseline=55.1%  gap=-4.5
# predicted class counts: {1: 111, 0: 67}
# fold 2: train=356 test=178  train_acc=52.0%  test_acc=46.1%  baseline=53.4%  gap=5.9
# predicted class counts: {1: 178}
# fold 3: train=534 test=178  train_acc=47.9%  test_acc=37.6%  baseline=62.4%  gap=10.3