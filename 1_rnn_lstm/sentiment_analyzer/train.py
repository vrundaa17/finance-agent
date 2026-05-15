import torch
import torch.nn as nn
import numpy as np 
import matplotlib.pyplot as plt
import pickle

from torch.utils.data import DataLoader, TensorDataset
from datasets import load_dataset

from utils import build_vocab, encode_text
from model import SentimentLSTM

print("Loading IMDB dataset...")
dataset = load_dataset("imdb")
train_data = dataset["train"]
test_data = dataset["test"]

print(f"Number - train - : {len(train_data)}")
print(f"Number - test - : {len(test_data)}")

vocab = build_vocab(train_data["text"])
print(f"vocab size : {len(vocab)}")

with open('vocab.pkl', 'wb') as f:
    pickle.dump(vocab,f)
print("Vocab saved")


MAX_LENGTH = 200
print("Encoding...")
train_encode = [encode_text(r, vocab, max_length=MAX_LENGTH) for r in train_data['text']]
test_encode = [encode_text(r, vocab, max_length=MAX_LENGTH) for r in test_data['text']]

X_train = torch.tensor(train_encode, dtype= torch.long)
y_train = torch.tensor(train_data['label'],dtype = torch.float32)
X_test = torch.tensor(test_encode, dtype= torch.long)
y_test = torch.tensor(test_data['label'],dtype= torch.float32)

BATCH_SIZE = 64
train_dataset = TensorDataset(X_train, y_train)
test_dataset = TensorDataset(X_test, y_test)

train_loader = DataLoader(train_dataset,batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE)


VOCAB_SIZE = len(vocab)
EMBED_SIZE = 128
HIDDEN_SIZE = 256
NUM_LAYERS = 2

model = SentimentLSTM(VOCAB_SIZE, EMBED_SIZE,BATCH_SIZE, HIDDEN_SIZE, NUM_LAYERS)
criterion = nn.BCELoss()
optimizer = torch.optim.Adam(model.parameters(), lr = 0.001)
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=5)

print(f"Total parameters : {sum(p.numel() for p in model.parameters())}")
print("\nStarting training...")

EPOCHS = 5
train_losses =[]
test_losses =[]
train_acc = []
test_acc =[]

for epoch in range(EPOCHS):
    model.train()
    correct = 0
    total =0
    
    for batch_idx, (inputs,labels) in enumerate(train_loader):
        labels = labels.unsqueeze(1)
        
        optimizer.zero_grad()
        hidden = model.init_hidden()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        
        