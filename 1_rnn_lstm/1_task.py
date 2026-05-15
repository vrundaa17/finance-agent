import torch
import torch.nn as nn
import numpy as np

text = "hello world of rnn, we are learning through pytorch for fxis"

# Create a set of all unique words
words = sorted(set(text.split()))
# print(f"Unique words : {words}")
# print(f"Total unique words : {len(words)}")

# Create a mapping of words to index and index to words
# hello - 1, world -2 like that but we have used sorted so it will be ascending order.
# this mapping is imp because we need to convert the text data into numerical data
word_to_index = { word : idx for idx, word in enumerate(words)}
index_to_word = { idx : word for idx, word in enumerate(words)}
# print(f"Word to index mapping : \n\t{word_to_index}")
print(f"Index to word mapping : \n\t{index_to_word}")

# Convert the text data into numerical data using the mapping
# Now the data will be represented with there index
encoded = [word_to_index[word] for word in text.split()]
# print(f"Encoded text : {encoded}")


sequence_length = 5

inputs=[]
targets=[]

for i in range(len(encoded) - sequence_length):
    input_seq = encoded[i : i + sequence_length]
    target_seq = encoded[i + 1 : i+sequence_length +1 ]
    inputs.append(input_seq)
    targets.append(target_seq)
inputs = torch.tensor(inputs, dtype = torch.long)
targets = torch.tensor(targets, dtype = torch.long)

print(f"Input sequences : \n{inputs}")
print(f"Target sequences : \n{targets}")

vocab_size = len(words)

input_onehot = nn.functional.one_hot(inputs, num_classes=vocab_size).float()
print(f"One-hot encoded input : \n{input_onehot}")




# RNN
    # the rnn layer in pytorch takes 
    # input of shape (seq_len, batch_size, input_size) and 
    # output of shape (seq_len, batch_size, hidden_size)
class TextRNN(nn.Module):
    def __init__(self, vocab_size, hidden_size):
        super(TextRNN, self).__init__()
        self.hidden_size = hidden_size
        self.rnn = nn.RNN(
            input_size= vocab_size,         # because we are using one-hot encoding, the input size is equal to the vocab size
            hidden_size = hidden_size,      # the number of features in the hidden state
            batch_first = True              # because we want the input and output tensors to have the shape (batch_size, seq_len, feature_size) 
        )
        self.fc = nn.Linear(hidden_size, vocab_size) # fully connected layer to map the hidden state to the output vocabulary size
        
    def forward(self,x,hidden):
        out, hidden = self.rnn(x,hidden)
        out = self.fc(out)
        return out, hidden
    
    def init_hidden(self, batch_size):
        return torch.zeros(1,batch_size, self.hidden_size)
    
hidden_size = 64
learning_rate =0.01
epochs = 100

model = TextRNN(vocab_size,hidden_size)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr = learning_rate)

print("Starting training...")
for epoch in range(epochs):
    hidden = model.init_hidden(batch_size = input_onehot.shape[0])
    optimizer.zero_grad()
    output,hidden = model(input_onehot, hidden)
    
    batch_size = output.shape[0]
    seq_len = output.shape[1]
    loss = criterion(output.view(batch_size*seq_len, vocab_size),
                     targets.view(batch_size*seq_len))
    
    loss.backward()
    optimizer.step()
    
    print(f"Epoch {epoch}, Loss: {loss.item():.4f}")
    

def generate(model, start_word,num_words):
    model.eval()
    current_idx = word_to_index[start_word]
    hidden = model.init_hidden(batch_size=1)
    generated = [start_word]
    
    for _ in range(num_words):
        x = torch.tensor([[current_idx]],dtype = torch.long)
        x = nn.functional.one_hot(x, num_classes=vocab_size).float()
        output, hidden = model(x, hidden)
        probabilities = torch.softmax(output[0,0],dim=0)
        current_idx = torch.multinomial(probabilities, 1).item()
        generated.append(index_to_word[current_idx])
        
    return ' '.join(generated)

print("Generated text : ", generate(model, start_word = "fxis", num_words=3))
    