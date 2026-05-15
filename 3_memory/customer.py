'''
Customer Chatbot :-

RunnableWithMemory 
FileChatMessageHistory
CallBackHandler
ChatHuggingFace

'''

import time
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_huggingface import HuggingFaceEndpoint,ChatHuggingFace

from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_core.messages import trim_messages, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler

from dotenv import load_dotenv
load_dotenv()


class CustomerCallback(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompt, **kwargs):
        print("LLM started...")
        self._start_time = time.time()
        
    def on_llm_error(self,error,**kwargs):
        print(f"LLM error : {repr(error)}")
        
    def on_llm_end(self,respons, **kwargs):
        end = time.time() - self._start_time
        print(f"LLM end in {end} ")
        
        

system_prompt='''
    You are a helpful, polite, and efficient customer support chatbot. 
    Your goal is to assist users by answering their questions, solving their problems, and guiding them through processes clearly.

        Follow these rules:
        -Be concise and clear in your responses.
        -Always be polite and professional.
        -If you don't know something, say so and suggest how the user can get help.
        -Ask clarifying questions when the user's request is unclear.
        -Focus on solving the user's issue in the fewest steps possible.
        -Avoid unnecessary jargon.
        -Never argue or show frustration.

        When responding:
        -Understand the user's intent.
        -Provide a direct answer or solution.
        -Offer next steps if needed.

    If the issue is complex, break the solution into simple steps.
'''

prompt = ChatPromptTemplate.from_messages([
    ('system' ,'{system_prompt}'),
    MessagesPlaceholder('history'),
    ('human','{input}')
])

hfe = HuggingFaceEndpoint(
    repo_id='meta-llama/Llama-3.1-8B-Instruct',
    temperature=0.7,
    max_new_tokens=512, 
    callbacks = [CustomerCallback()]
)
llm = ChatHuggingFace(llm=hfe)
chain = prompt | llm 

store = {}

def get_session(session_id):
    if session_id not in store :
        store[session_id] = FileChatMessageHistory(f'{session_id}.json')
    return store[session_id]


def summarizer(messages):
    if len(messages)>2:
        return None
    summary_prompt ='''
        Summarise the text for long-term memory. Donot remove the key informations.
        {messages}
    '''
    res = llm.invoke(summary_prompt).content
    return res
        

def memory(session_id):
    history = get_session(session_id)
    
    messages = history.messages
    summary = summarizer(messages)
    
    if summary :
        trim = [
            SystemMessage(content = f'Conversation Summary : {summary}')
        ] + messages[-4:]

    else:
        trim = trim_messages(
            messages, max_tokens= 5, token_counter = len, strategy='last'
        )
    
    history.clear()
    for m in trim:
        history.add_message(m)
    
    return history



memory_chain = RunnableWithMessageHistory(
    chain, memory ,input_messages_key ='input', history_messages_key='history'
)

name = input("Your name :")
if __name__ =='__main__':
    while True :
        user_input= input('You : ')
        
        if user_input.lower() =='exit':
            print('bye bye ending...')
            break
        
        res =memory_chain.invoke(
            {'system_prompt':system_prompt,'input':user_input},
            config = {'configurable' : {'session_id': name}}
            )
        
        print(f'AI : {res.content}')
    