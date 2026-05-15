from langchain_huggingface import HuggingFaceEndpoint, HuggingFacePipeline, ChatHuggingFace
from transformers import pipeline
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

llm = HuggingFaceEndpoint(
    repo_id ="google/flan-t5-small",
    task="text2text-generation",
    model_kwargs={"temperature": 0.7, "max_length": 512},
)

ans = llm.invoke("What is the capital of France?")
print(ans)


pipe = pipeline("text-generation", model= "google/flan-t5-small") # device = 0 means using GPU, -1 means using CPU
llm1 = HuggingFacePipeline(pipeline= pipe)
ans1 = llm1.invoke("What is the capital of France?")
print(ans1)

chat_llm = ChatHuggingFace(
    repo_id="google/flan-t5-small",
    task="text2text-generation",
    model_kwargs={"temperature": 0.7, "max_length": 512},
)
ans2 = chat_llm.invoke([
    SystemMessage(content="You are a helpful assistant that provides concise answers to questions."),
    HumanMessage(content="What is the capital of France?")])
print(ans2)

# ChatPromptTemplate
#    ↓
# messages
#    ↓
# LangChain converts → string prompt
#    ↓
# HuggingFacePipeline / Endpoint
#    ↓
# model generates text
#    ↓
# LLMResult / string returned

# | Type                      | Where model runs             | Control | Speed              | Cost           |
# | ------------------------- | ---------------------------- | ------- | ------------------ | -------------- |
# | **Hugging Face Endpoint** | Cloud (Hugging Face servers) | Low     | Fast               | Paid/free tier |
# | **Pipeline**              | Your machine (local)         | High    | Depends on your PC | Free           |

# | Wrapper               | Backed by          |
# | --------------------- | ------------------ |
# | `HuggingFaceEndpoint` | Cloud API          |
# | `HuggingFacePipeline` | Local Transformers |



# | Feature    | invoke      | batch            | astream               |
# | ---------- | ----------- | ---------------- | --------------------- |
# | Calls      | 1           | many             | 1 (async)             |
# | Sync/Async | sync        | sync             | async                 |
# | Output     | full text   | list of texts    | streaming chunks      |
# | Speed      | normal      | fastest for bulk | best UX for streaming |
# | Use case   | simple apps | bulk processing  | chatbots/UI apps      |



# User Input
#     ↓
# Load chat history
#     ↓
# MessagesPlaceholder inserts history
#     ↓
# Prompt sent to LLM
#     ↓
# Save new messages
