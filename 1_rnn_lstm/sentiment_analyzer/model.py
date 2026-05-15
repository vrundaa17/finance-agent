import torch
import torch.nn as nn


class SentimentLSTM(nn.Module):
    def __init__(self, vocab_size, embed_size, batch_size, hidden_size, num_layers):
        super(SentimentLSTM, self).__init__()
        
        self.batch_size = batch_size
        self.hidden_size = hidden_size
        
        self.embed = nn.Embedding(vocab_size, embed_size, padding_idx =0) # padding_idx if not 0 why we need to do this because we are using padding to make all the sequences of the same length and we don't want the padding to affect the learning process so we set the padding index to 0 and the embedding layer will ignore the padding index when updating the weights
        
        self.lstm = nn.LSTM(
            input_size = embed_size,
            hidden_size = hidden_size,
            num_layers = num_layers,
            batch_first = True,
            bidirectional = True # because we want to capture the context from both directions in the text data
        )
        
        self.fc = nn.Linear(hidden_size * 2,1)  # because we are using bidirectional lstm so the hidden size will be multiplied by 2 and the output will be a single value between 0 and 1 because we are using sigmoid activation function in the output layer for binary classification
        
        self.sigmoid = nn.Sigmoid()
        
    def forward(self,x):
        embedded = self.embed(x)
        lstm_out,(hidden,cell) = self.lstm(embedded, hidden) 
        
        hidden_forward = hidden[-2,:,:]
        hidden_backward = hidden[-1,:,:] 
        hidden_combined= torch.cat((hidden_forward, hidden_backward),dim=1)
        
        out = self.fc(hidden_combined)
        
        return self.sigmoid(out)
    
    def init_hidden(self):
        h0 = torch.zeros(self.num_layers * 2, self.batch_size, self.hidden_size)
        c0 = torch.zeros(self.num_layers * 2 , self.batch_size, self.hidden_size)
        return(h0,c0)