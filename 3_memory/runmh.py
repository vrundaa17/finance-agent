'''
this is the example of RunnableWithMemory

'''

from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory, FileChatMessageHistory
from langchain_groq import ChatGroq
from langchain_core.messages import trim_messages

from dotenv import load_dotenv
load_dotenv()

llm = ChatGroq(model='llama-3.1-8b-instant')

prompt = ChatPromptTemplate.from_messages([
    ('system','You are a helpful assistant.'),
    MessagesPlaceholder('history'),
    ('human', '{input}')
])

chain = prompt | llm

store = {}

def get_history(session_id : str):
    if session_id not in store:
        store[session_id]= FileChatMessageHistory(f'{session_id}.json')
    # history = store[session_id]
    # trimmed = trim_messages(history.messages, strategy="last",max_tokens=3, token_counter=len)
    # history.clear()
    # for m in trimmed:
    #     history.add_message(m)
    # return history
    return store[session_id ]
    
chain_with_memory = RunnableWithMessageHistory(
    chain,
    get_history,
    input_messages_key='input',
    history_messages_key='history'
)
ask = input('human : ')
response = chain_with_memory.invoke(
    {'input': ask},
    config = {'configurable': {'session_id': 'user1'}}
)
print(f'AI : {response.content}')
ask = input('human : ')
response2 = chain_with_memory.invoke(
    {'input':ask},
    config = {'configurable': {'session_id': 'user1'}}
)
print(f'AI : {response2.content}')


    
