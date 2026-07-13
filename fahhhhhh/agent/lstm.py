import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader,TensorDataset
import torch.nn as nn
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
from find import get_price_history
import ta
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


def features(closes, volumes,high,low):
    df = pd.DataFrame({"close": closes, "volume": volumes,"high":high,"low":low})
    
    df["return_1d"]= df["close"].pct_change(1)
    df["return_3d"]= df["close"].pct_change(3)
    df["return_5d"]= df["close"].pct_change(5)
    df["ma5"]= df["close"].rolling(5).mean()
    df["ma20"]= df["close"].rolling(20).mean()
    df["price_vs_ma5"]= df["close"] / df["ma5"]
    df["price_vs_ma20"]= df["close"] / df["ma20"]
    df["volatility"]= df["return_1d"].rolling(5).std()
    df["volume_change"]= df["volume"].pct_change(1)
    df["volume_vs_ma"]= df["volume"] / df["volume"].rolling(5).mean()
    df["RSI"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    df["MACD"] = ta.trend.MACD(df["close"]).macd()
    df["ADX"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()

    # df["CCI"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"]).cci()

    df["ATR"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()

    bb = ta.volatility.BollingerBands(df["close"])
    df["return_lag1"] = df["return_1d"].shift(1)
    df["return_lag2"] = df["return_1d"].shift(2)
    df["return_lag3"] = df["return_1d"].shift(3)
    df["bb_width"] = bb.bollinger_wband()
    df["bb_position"] = (df["close"] - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband())
    
    df["target"] = (df["close"].shift(-5) > df["close"]).astype(int)
    return df.dropna()

def create_seq(X,y,window=10):
    Xs, ys = [],[]
    for i in range(len(X) - window):
        Xs.append(X[i:i+ window])
        ys.append(y[i+window])
    return np.array(Xs), np.array(ys)


class LSTMmodel(nn.Module):
    def __init__(self,input_size, num_layers=2,hidden_size=32):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size = input_size,
            hidden_size = hidden_size,
            num_layers = num_layers,
            dropout=0.2,
            batch_first=True,
        )
        # self.bn = nn.BatchNorm1d(hidden_size)
        # self.fc1 = nn.Linear(hidden_size,32)
        # self.relu = nn.ReLU()
        # # self.fc2 = nn.Linear(32,1)
        # self.sig = nn.Sigmoid()
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            
            nn.Linear(32, 1)
        )
        
    def forward(self,x):
        out,_ =self.lstm(x)
        return self.fc(out[:, -1, :])
    

class GRUmodel(nn.Module):
    def __init__(self,input_size, num_layers=2,hidden_size=32):
        super().__init__()
        self.lstm = nn.GRU(
            input_size = input_size,
            hidden_size = hidden_size,
            num_layers = num_layers,
            dropout=0.2,
            batch_first=True,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
    def forward(self,x):
        out,_ =self.lstm(x)
        return self.fc(out[:, -1, :])

def xgb_baseline(X_train, y_train, X_test, y_test):
    model = XGBClassifier(n_estimators=300,max_depth=4,learning_rate=0.01,
        subsample=0.5,colsample_bytree=0.5,random_state=42,eval_metric="logloss")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    acc = round(accuracy_score(y_test, preds) * 100, 1)
    print("xgboost accuracy:", acc)
    return acc

def train(model,X_train,y_train,X_val,y_val, epochs=50,batch_size=16):
    device= torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model= model.to(device)
    optimiser = torch.optim.Adam(model.parameters(),lr=0.001, weight_decay=1e-4)
    criterion = nn.BCEWithLogitsLoss()
    
    X_t = torch.FloatTensor(X_train).to(device)
    y_t = torch.FloatTensor(y_train).unsqueeze(1).to(device)
    X_v = torch.FloatTensor(X_val).to(device)
    y_v = torch.FloatTensor(y_val).unsqueeze(1).to(device)
    
    dataset = TensorDataset(X_t,y_t)
    dataloader =DataLoader(dataset,batch_size=batch_size, shuffle=False)
    
    best_val_loss = float("inf")
    best_state = None
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for xb,yb in dataloader:
            optimiser.zero_grad()
            loss = criterion(model(xb),yb)
            loss.backward()
            optimiser.step()
            total_loss += loss.item()
        model.eval()
        with torch.no_grad():
            val_loss = criterion(model(X_v), y_v).item()
            
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k,v in model.state_dict().items()}

        if epoch % 5 == 0:
            print(f"epoch {epoch} train_loss {total_loss/len(dataloader):.4f} val_loss {val_loss:.4f}")
    model.load_state_dict(best_state)
    print(f"restored best model, val_loss={best_val_loss:.4f}")
    return model, device



def train_pred_multi(tickers, period="8y"):
    feature_cols = [
        "return_1d", "return_3d", "return_5d","price_vs_ma5", "price_vs_ma20",
        "volatility", "volume_vs_ma","RSI", "MACD", "ADX", "ATR", "bb_width",'nifty_return'
    ]
    window = 5
    
    nifty_hist = get_price_history("^NSEI", period)
    nifty_df = pd.DataFrame({"close": nifty_hist["close"]})
    nifty_df["nifty_return"] = nifty_df["close"].pct_change(1)
    nifty_return_series = nifty_df["nifty_return"].values
    
    all_X_train, all_y_train = [], []
    all_X_test, all_y_test = [], []
    last_ticker_data = None
    
    for sname in tickers:
        try:
            hist = get_price_history(sname,period)
        except Exception as e:
            print(f"skip {sname}: {e}")
            continue
        
        closes = hist.get("close", [])
        volumes = hist.get("volume", [])
        high = hist.get("high",[])
        low = hist.get("low",[])
        if len(closes) < 60:
            continue
        
        df = features(closes, volumes,high,low)
        n = min(len(df), len(nifty_return_series))
        df = df.iloc[-n:].copy()
        df["nifty_return"] = nifty_return_series[-n:]
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        if len(df) < 40:
            continue
        
        X = df[feature_cols]
        y = df["target"].to_numpy()
        

        split = int(len(X) * 0.8)
        scaler = StandardScaler()
        
        X_train_scaled = scaler.fit_transform(X[:split])
        X_test_scaled = scaler.transform(X[split:])
        X_scaled = np.vstack((X_train_scaled, X_test_scaled))
        X_seq, y_seq = create_seq(X_scaled, y, window=window)
        
        split_seq = int(len(X_seq) * 0.8)

        all_X_train.append(X_seq[:split_seq])
        all_y_train.append(y_seq[:split_seq])
        all_X_test.append(X_seq[split_seq:])
        all_y_test.append(y_seq[split_seq:])

        last_ticker_data=(X_scaled,closes[-1],sname)
        
        
    X_train = np.vstack(all_X_train)
    y_train = np.concatenate(all_y_train)
    X_test = np.vstack(all_X_test)
    y_test = np.concatenate(all_y_test)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.15, shuffle=False
    )
    # xgb_baseline(X_train,y_train,X_test,y_test)
    print("multi : ",len(X_train, ),"test :", len(X_test))
    
    input_size = len(feature_cols)
    model = LSTMmodel(input_size=input_size)
    model, device = train(model, X_train, y_train,X_val,y_val, epochs=20, batch_size=16)

    model.eval()
    with torch.no_grad():
        X_test_t = torch.FloatTensor(X_test).to(device)
        logits = model(X_test_t)
        y_pred_prob = torch.sigmoid(logits).cpu().numpy().flatten()
        y_pred = (y_pred_prob > 0.5).astype(int)
        
    accuracy = round(accuracy_score(y_test, y_pred) * 100, 1)
    baseline_acc = round(max(y_test.mean(), 1 - y_test.mean()) * 100, 1)
    print("baseline:", baseline_acc, "model:", accuracy)
    print("pred UP ratio:", y_pred.mean(), "actual UP ratio:", y_test.mean())

    return {"accuracy": accuracy, "baseline": baseline_acc}

        
if __name__=="__main__":
    # from find import get_price_history
    # hist = get_price_history("RELIANCE.NS","5y")
    stocks=['TATAPOWER.NS','^NSEI','TATACOMM.NS','TATAELXSI.NS','TITAN.NS','TMCV.NS',
            'TATASTEEL.NS','TCS.NS','TATACONSUM.NS','TATACHEM.NS']
    result =train_pred_multi(stocks)
    print(result)