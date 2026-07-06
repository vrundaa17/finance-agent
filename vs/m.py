from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()

MODEL="llama-3.1-8b-instant"
def call_llm(text, last_insert,history):
    prompt = ChatPromptTemplate.from_template("""
        You are a voice editing assistant.
        If the user asks to change, rewrite, improve, fix grammar, shorten,
        or rephrase something, assume they mean the previous dictated text.
        Return ONLY the edited text.
        
        Previous text:
            {last_insert}

        Conversation history:
            {history}

        User instruction:
            {text}
        Rules:
        - Return ONLY the edited text.
        - Do NOT explain your changes.
        - Do NOT add notes.
        - Do NOT use markdown.
        - Output exactly one edited sentence.
    """)

    model = ChatGroq(model=MODEL)
    chain = prompt|model

    result = chain.invoke({
        'text':text,
        'last_insert':last_insert,
        'history':history,
    })
    return result.content

