import torch 
import re
from collections import Counter

def tokenise(text):
    text = text.lower()
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"[^a-zA-Z1-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.split()


def build_vocab(texts, max_vocab=10000):
    counter = Counter()
    for text in texts :
        tokens = tokenise(text)
        counter.update(tokens)
    
    most_common = counter.most_common(max_vocab-2)
    
    vocab = {"<PAD>": 0, "<UNK>": 1}
    for word,_ in most_common:
        vocab[word] = len(vocab)
    return vocab


def encode_text(text,vocab, max_length=200):
    tokens = tokenise(text)
    encode = [vocab.get(token,1) for token in tokens]
    
    if len(encode) < max_length:
        encode = encode +[0] * (max_length - len(encode))
    else:
        encode = encode[:max_length]
    
    return encode