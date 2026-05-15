import PyPDF2
# import docx
import numpy as np
import re
from nltk.tokenize import sent_tokenize
from keybert import KeyBERT
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sklearn.feature_extraction.text import TfidfVectorizer


def extract_text(file):

    text =""
    
    if file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        
        for page in reader.pages:
            page = page.extract_text()
            if page:
                text += page
            
    # elif file.name.endswith('.docx'):
    #     try:
    #         file.seek(0) 
    #         doc = docx.Document(file)
    #         for para in doc.paragraphs:
    #             text += para.text + '\n'
    #     except Exception as e:
    #         raise ValueError("The uploaded DOCX file is invalid or corrupted") from e
  
    elif file.name.endswith('.txt'):
        file.seek(0)
        text += file.read().decode('utf-8')  
    else:
        raise ValueError("Unsupported file format. Only .pdf, .docx, .txt")
        
    return text


def clean_text(raw_text):

    text = re.sub(r'\n+', '. ', raw_text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r"[^a-zA-Z0-9,.:;!?()'\s-]", ' ', text)
    text = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', text)
    text = text.strip()
    return text
    
    
def remove_stopwords(cleaned_text):
    sentences = sent_tokenize(cleaned_text)
    return sentences


kw_model = KeyBERT()
tokenizer = AutoTokenizer.from_pretrained("valhalla/t5-small-qg-hl")
model = AutoModelForSeq2SeqLM.from_pretrained("valhalla/t5-small-qg-hl")


def rank_sentences_tfidf(sentences, top_n=10):

    sentences = [s for s in sentences if len(s.split()) > 6]

    if len(sentences) == 0:
        return []

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(sentences)

    sentence_scores = tfidf_matrix.sum(axis=1)
    scores = np.array(sentence_scores).flatten()
    top_indices = np.argsort(scores)[-top_n:][::-1]
    ranked_sentences = [sentences[i] for i in top_indices]

    return ranked_sentences


def generate_questions(context,answer):
    
    input_text = f"generate question: {context} answer: {answer}"
    inputs = tokenizer.encode(input_text,return_tensors='pt',max_length=512,truncation=True)
    outputs = model.generate(inputs,max_length=64)
    
    question = tokenizer.decode(outputs[0],skip_special_tokens=True)
    
    return question



def generate_faq(sentences):
    
    ranked_sentences = rank_sentences_tfidf(sentences, top_n=10)
    
    faq=[]
    for sent in ranked_sentences:
        question = generate_questions(sent, sent)  
        

        faq.append({
            "question": question,
            "answer": sent
        })

    
    return faq
    
    
