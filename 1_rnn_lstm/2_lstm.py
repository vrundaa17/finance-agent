import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import random

text = """LSTM is a type of recurrent neural network architecture that is designed to handle long-term dependencies in sequential data. It was introduced by Hochreiter and Schmidhuber in 1997 as a solution to the vanishing gradient problem that traditional RNNs face when trying to learn from long sequences. the key innovation of LSTM is the introduction of memory cells and gating mechanisms that allow the network to selectively retain or forget information over time. This makes LSTM particularly effective for tasks such as language modeling, machine translation, and time series prediction, where understanding context and long-term dependencies is crucial."""

words = text.split()
print(f"Total words : {len(words)}")

vocab = sorted(set(words))
vocab_size = len(vocab)
print(f"Unique words : {vocab}")
print(f"Total unique words : {vocab_size}")

word_to_index = {word : idx for idx, word in enumerate(vocab)}
index_to_word = { idx:word for idx,word in enumerate(vocab)}
print(f"Word to index mapping : \n\t{word_to_index}")

encoded = [word_to_index[word] for word in words]
print(f"Encoded text : \n{encoded}")

sequence_length = 5

inputs =[]
targets =[]

for i in range(len(encoded) - sequence_length):
    input_seq = encoded[i : i+sequence_length]
    target_seq = encoded[i+1 : i+sequence_length + 1]
    inputs.append(input_seq)
    targets.append(target_seq)  

inputs = torch.tensor(inputs, dtype= torch.long)
targets = torch.tensor(targets, dtype=torch.long)

print(f"Input shape: {inputs.shape}")
print(f"Target shape: {targets.shape}")


class LSTM(nn.Module):
    def __init__(self, vocab_size, embed_size, hidden_size, num_layers):
        super(LSTM,self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.embedding = nn.Embedding(vocab_size, embed_size)
        
        self.lstm = nn.LSTM(
            input_size = embed_size,    # because we are using embedding layer, the input size is equal to the embed size
            hidden_size = hidden_size,
            num_layers = num_layers,
            batch_first = True
        )
        
        self.fc = nn.Linear(hidden_size,vocab_size)
        
    def forward(self, x, hidden):
        embedded = self.embedding(x)
        out, hidden = self.lstm(embedded, hidden)
        out = out[:,-1,:] # we only want the output of the last time step that is the output of the last word in the sequence for example if the input sequence is "the cat sat on the" we only want the output of the last word "the"
        out = self.fc(out)
        return out, hidden
    
    def init_hidden(self, batch_size):
        h0 = torch.zeros(self.num_layers, batch_size, self.hidden_size)
        c0 = torch.zeros(self.num_layers, batch_size, self.hidden_size)
        return (h0,c0)
    
    
embed_size = 64
hidden_size = 128
num_layers = 2
learning_rate = 0.001
epochs = 400
batch_size = 16

model = LSTM(vocab_size, embed_size, hidden_size, num_layers)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr= learning_rate)

print("Starting training...")

def get_batches(inputs, targets,batch_size):
    # this function will return a random batch of input and target sequences of size batch_size
    # this is mainly for training the model in batches instead of feeding the entire dataset at once which can be memory intensive and also helps in faster convergence
    # why do we do this  [ like the batch training but randomly sampling the batches instead of sequentially ]
        # 1. it helps in faster convergence because the model can learn from a smaller subset of the data at a time and update the weights more frequently which can lead to faster convergence
        # 2. it helps in regularization because the model is exposed to different subsets of
        # the data in each epoch which can help in preventing overfitting and improving generalization
    indices = random.sample(range(len(inputs)), batch_size )
    batch_inputs = inputs[indices]
    batch_targets = targets[indices]
    return batch_inputs, batch_targets


for epoch in range(epochs):
    model.train()
    batch_inputs, batch_targets = get_batches(inputs, targets, batch_size)
    
    hidden = model.init_hidden(batch_size)
    optimizer.zero_grad()
    
    output, hidden = model(batch_inputs, hidden)
    loss = criterion(output,batch_targets[:,-1])
    loss.backward()
    optimizer.step()
    
    if (epoch%50)==0:
        print(f"Epoch [{epoch}/{epochs}], Loss: {loss.item():.4f}")
        

def generate(model, start_word, num_words=20):
    model.eval()
    for w in start_word:
        if w not in word_to_index:
            print(f"Word '{w}' not in vocabulary.")
            return
        
    generated = start_word.copy()
    input_seq = [word_to_index[w] for w in start_word]
    hidden = model.init_hidden(batch_size=1)
    
    for _ in range(num_words):
        current_seq = input_seq[-sequence_length:]  # get the last 'sequence_length' words for example if the generated sequence is "the cat sat on the" and the sequence length is 5 we will take the last 5 words "the cat sat on the" as the input sequence for the next prediction
        x = torch.tensor([current_seq], dtype= torch.long)
        with torch.no_grad():
            output, hidden = model(x, hidden)
        
        probab = F.softmax(output[0], dim=0)
        next = torch.multinomial(probab, 1).item()
        generated.append(index_to_word[next])
        input_seq.append(next)      # we need to append the predicted word index to the input sequence so that it can be used for the next prediction in the next iteration of the loop this is because we have num_length of 20 
    return ' '.join(generated)


print(generate(model, ["LSTM", "is", "a", "type", "of"], 
                    num_words=15))