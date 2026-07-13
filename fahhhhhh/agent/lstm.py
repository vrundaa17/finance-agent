import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader,TensorDataset
import torch.nn as nn
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler



def features(closes, volumes):
    df = pd.DataFrame({"close": closes, "volume": volumes})
    
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

    delta = df["close"].diff()
    gain= delta.clip(lower=0).rolling(14).mean()
    loss= (-delta.clip(upper=0)).rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + gain / loss))

    ema12 = df["close"].ewm(span=12).mean()
    ema26= df["close"].ewm(span=26).mean()
    df["macd"]= ema12 - ema26
    df["macd_diff"] =df["macd"] - df["macd"].ewm(span=9).mean()

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


def train(model,X_train,y_train, epochs=50,batch_size=16):
    device= torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model= model.to(device)
    optimiser = torch.optim.Adam(model.parameters(),lr=0.001, weight_decay=1e-4)
    criterion = nn.BCEWithLogitsLoss()
    
    X_t = torch.FloatTensor(X_train).to(device)
    y_t = torch.FloatTensor(y_train).unsqueeze(1).to(device)
    
    dataset = TensorDataset(X_t,y_t)
    dataloader =DataLoader(dataset,batch_size=batch_size, shuffle=False)
    
    model.train()
    
    for epoch in range(epochs):
        total_loss = 0
        for xb,yb in dataloader:
            optimiser.zero_grad()
            loss = criterion(model(xb),yb)
            loss.backward()
            optimiser.step()
            total_loss += loss.item()
        if epoch % 10 == 0:
            print(f"epoch {epoch} loss {total_loss/len(dataloader):.4f}")
    return model,device


def train_pred(price_history:dict):
    closes = price_history.get("close",[])
    volumes = price_history.get("volume",[])
    
    if len(closes)<60:
        return {"error":"At least 60 days of history"}
    
    feature_cols = ["return_1d", "return_3d", "return_5d","price_vs_ma5", "price_vs_ma20",
        "volatility", "volume_change", "volume_vs_ma","rsi", "macd", "macd_diff"]
    
    df = features(closes,volumes)
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    
    X = df[feature_cols].values
    y = df['target'].values
    
    split = int(len(X)*0.8)
    scaler = StandardScaler()
    
    X_train_scaled = scaler.fit_transform(X[:split])
    X_test_scaled = scaler.transform(X[split:])
    X_scaled = np.vstack((X_train_scaled, X_test_scaled))

    window = 5
    X_seq, y_seq = create_seq(X_scaled, y, window=window)

    split_seq = int(len(X_seq) * 0.8)
    X_train, X_test = X_seq[:split_seq], X_seq[split_seq:]
    y_train, y_test = y_seq[:split_seq], y_seq[split_seq:]

    
    if len(X_train)<20:
        return{"error":"Quit a few data to predict"}
    
    input_size = len(feature_cols)
    model = LSTMmodel(input_size=input_size)
    model,device = train(model,X_train,y_train,epochs=40,batch_size=32)
    
    model.eval()
    with torch.no_grad():
        X_test_t= torch.FloatTensor(X_test).to(device)
        logits = model(X_test_t)

        y_pred_prob = torch.sigmoid(logits).cpu().numpy().flatten()
        y_pred = (y_pred_prob > 0.5).astype(int)
        
    
    accuracy = round(accuracy_score(y_test,y_pred)*100,1)
    baseline_acc = round(max(y_test.mean(), 1 - y_test.mean()) * 100, 1)
    print("baseline:", baseline_acc, "model:", accuracy)
    print("pred UP ratio:", y_pred.mean(), "actual UP ratio:", y_test.mean())
    with torch.no_grad():
        latest = torch.FloatTensor(X_scaled[-window:].reshape(1, window, input_size)).to(device)
        logits = model(latest)
        prob = float(torch.sigmoid(logits).cpu().numpy()[0][0])
    
    confidence = round(max(prob, 1 - prob) * 100)
    direction= "UP" if prob>0.5 else "DOWN"
    
    return {
    "direction": str(direction),
    "confidence": float(confidence),
    "accuracy": float(accuracy),
    "current_price": float(closes[-1]),
    "training_days": len(X_train),
    "test_days": len(X_test),
    "disclaimer": "ML prediction only. Not financial advice. Backtest accuracy does not guarantee future results."
}
    
    
if __name__=="__main__":
    from find import get_price_history
    hist = get_price_history("RELIANCE.NS","5y")
    result =train_pred(hist)
    print(result)