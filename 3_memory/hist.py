from dotenv import load_dotenv
load_dotenv()
from langchain_community.chat_message_histories import ChatMessageHistory, FileChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage


from langchain_groq import ChatGroq
# history = ChatMessageHistory()        # RAM 
history = FileChatMessageHistory('hist.json') #file so preserved......

history.add_ai_message("Hello, how can I help you?")
history.add_user_message("I am Raj. I want to know the capital of India.")
history.add_ai_message("India's capital is Delhi")

print(history)

llm = ChatGroq(model='llama-3.1-8b-instant')

# template = '''You are a helping assistant. Help them with there problems.
# '''

prompt = ChatPromptTemplate.from_messages([
    ('system','You are a helping assistant.'),
    MessagesPlaceholder('history'),
    ('human' , "Which country's capital I was asking of?")
])

chain = prompt | llm 
print(chain.invoke({'history' : history.messages}).content)
# .....




