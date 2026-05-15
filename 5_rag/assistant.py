# imports and load env
from langchain_community.document_loaders import PyPDFLoader, CSVLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.vectorstores import Chroma

from langchain_huggingface import HuggingFaceEmbeddings, ChatHuggingFace, HuggingFaceEndpoint
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

from langchain_classic.retrievers.document_compressors.cross_encoder_rerank import CrossEncoderReranker
from langchain_classic.retrievers import ContextualCompressionRetriever

from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory

from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

import os
from dotenv import load_dotenv
load_dotenv()
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
hfe = HuggingFaceEndpoint(repo_id="meta-llama/Llama-3.1-8B-Instruct")
llm = ChatHuggingFace(llm=hfe)
os.environ['LANGCHAIN_TRACING_V2']='true'
os.environ['LANGCHAIN_PROJECT']='rarara'

# load PDF — ask user for filename at start
def build_load_file(filename):
    loader = PyPDFLoader(filename)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size= 1000, chunk_overlap=120)
    chunks = splitter.split_documents(docs)
    print(f"Loaded {len(docs)} pages, split into {len(chunks)} chunks")
    return chunks

def build_vector_store(chunks, model, persist_dir):
    embeddings = HuggingFaceEmbeddings(model_name=model)
    
    if os.path.exists(persist_dir) and os.listdir(persist_dir):
        print("Loading existing vector store...")
        vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings
        )
    else:
        print("Creating new vector store...")
        vectorstore = Chroma.from_documents(
            chunks, 
            embeddings, 
            persist_directory=persist_dir
        )
        vectorstore.persist()
    return vectorstore


# build hybrid retriever — BM25 + semantic ensemble
def build_hybrid_ret(chunks, vectorstore):
    bm25= BM25Retriever.from_documents(chunks)
    bm25.k=3
    
    semantic = vectorstore.as_retriever(
        search_type='similarity',
        search_kwargs={'k':3}
    )
    
    ensemble = EnsembleRetriever(
        retrievers= [bm25, semantic],
        weights =[0.5,0.5]
    )
    
    return ensemble
    
    
# wrap with crossencoder reranker
def build_reranker(ensemble):
    cross_encoder = HuggingFaceCrossEncoder(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    ranking = CrossEncoderReranker(model=cross_encoder, top_n=3)
    
    reranking_retriever = ContextualCompressionRetriever(
        base_compressor = ranking,
        base_retriever = ensemble
    )
    
    return reranking_retriever
    
    
# wrap with history aware retriever
def build_history_retriever(llm, reranking_retriever):
    history_prompt = ChatPromptTemplate.from_messages([
        ("system", """Given a chat history and the latest user question,
        rewrite it into a standalone question that can be understood 
        without the chat history. Do not answer, just rewrite."""),
        MessagesPlaceholder("history"),
        ("human", "{input}")
    ])
    
    history = create_history_aware_retriever(
        llm= llm,
        prompt = history_prompt,
        retriever = reranking_retriever
    )
    
    return history
    

# build RAG prompt with citation instructions
def build_rag_chain(llm,history_retriever,):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful study assistant. 
        Answer using only the context below.
        At the end of your answer always write:
        Source: [filename] | Page: [page number]
        If the answer is not in the context say exactly:
        I don't have information about this in your document.
        
        Context: {context}"""),
        MessagesPlaceholder("history"),
        ("human", "{input}")
    ])
    
    doc_chain = create_stuff_documents_chain(llm, prompt)
    retriever = create_retrieval_chain(retriever = history_retriever, combine_docs_chain = doc_chain)
    return retriever

# wrap with memory
def build_memory_chain(session_dir,rag_chain):
    store ={}
    def get_session(session_id):
        if session_id not in store:
            os.makedirs(session_dir, exist_ok=True)
            store[session_id] = FileChatMessageHistory(
                f"{session_dir}/{session_id}.json"
            )
        return store[session_id]
    
    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        get_session,
        input_messages_key='input',
        history_messages_key='history'
    )
    return chain_with_history

# out of context check function using similarity_search_with_score
def out_of_context(vectorstore, question, threshold: float=0.5):
    result =vectorstore.similarity_search_with_score(question, k=1)
    if not result :
        return True
    
    score = result[0][1]
    return score>threshold
        
def citation(response:dict):
    source = []
    for doc in response.get('context',[]):
        meta = doc.metadata.get('source','unknown')
        page = doc.metadata.get('page','unknown')
        source.append(f'Page : {page}')
    return source

    

# chat loop
# - get user input
# - check if out of context first
# - if in context: invoke chain, print answer + sources
# - if out of context: print I don't know message
# - print retrieved page numbers after every answer
#checking

def create_rag_chain(file):
    
    chunks= build_load_file(file)
    vectorstore = build_vector_store(chunks,EMBEDDING_MODEL,'./sa_db')
    hybrid_retriever = build_hybrid_ret(chunks, vectorstore)
    reranker = build_reranker(hybrid_retriever)
    history_retriever = build_history_retriever(llm,reranker)
    rag_chain = build_rag_chain(llm,history_retriever)
    memory_chain = build_memory_chain( './session',rag_chain)
    return memory_chain
    
    
def ask_question(chain,question, session_id='newww'):
    response = chain.invoke(
        {"input": question},
        config={"configurable": {"session_id": session_id}}
    )

    return {
        "answer": response["answer"],
        "sources": citation(response)
    }


