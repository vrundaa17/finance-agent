from langgraph.graph import StateGraph, START,END
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict, List
from dotenv import load_dotenv
load_dotenv()

import os
os.environ['LANGCHAIN_TRACING_V2']='true'
os.environ['LANGCHAIN_PROJECT']='research-evals'
from langsmith import Client
from langsmith.evaluation import evaluate
client = Client()

class SupervisorState(TypedDict):
    task: str
    agent_to_call : str
    result : str

class ResearchState(TypedDict):
    questions: str
    search_queries : List[str]
    iterations: int
    results : List[str]
    is_sufficient : bool
    final_answer : str
    
    
    
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

def plan_node(state: ResearchState):
    
    question = state['questions']
    response = llm.invoke(f"Generate 3 search queries for this question. Return as numbered list. Question: {question}")
    lines = response.content.strip().split('\n')[1:]
    queries =[line.strip() for line in lines if line.strip()]
    
    return {'search_queries': queries}


search_tool = DuckDuckGoSearchRun()
def search_node(state: ResearchState):
    
    queries = state['search_queries']
    iteration = state['iterations']
    
    if iteration >= len(queries):
        current_query = queries[-1]
    else :
        current_query = queries[iteration]
        
    result = search_tool.run(current_query)
    return {
        'results' : state['results'] + [result],
        'iterations' : state['iterations'] + 1
    }
    

def evaluate_node(state: ResearchState):
    questions = state['questions']
    result = ' '.join(state['results'])
    
    result = llm.invoke(f"""Given this question and search results, 
    do you have enough information to write a comprehensive answer?
    Reply with only YES or NO.
    
    Question: {questions}
    Results: {result}""")
    
    answer = result.content.strip().lower()
    if 'yes' in answer:
        return {'is_sufficient' : True}
    else :
        return {'is_sufficient' : False}
    
    
def write_node(state: ResearchState):
    questions = state['questions']
    result = state['results']
    response = llm.invoke(f'''Using these search results, write a comprehensive structured
        answer with clear sections and key points.
        
        Question : {questions}
        Search Results : {result}
        ''')
    return {'final_answer' : response.content}


def research_conditional(state : ResearchState):
    if (state['is_sufficient']) or state['iterations']>3:
        return 'write'
    return 'search'


def ResearchNode(state: SupervisorState):
    research_graph = StateGraph(ResearchState)
    
    research_graph.add_node('plan',plan_node)
    research_graph.add_node('search',search_node)
    research_graph.add_node('evaluate',evaluate_node)
    research_graph.add_node('write',write_node)
    
    research_graph.set_entry_point('plan')
    research_graph.add_edge('plan','search')
    research_graph.add_edge('search','evaluate')
    research_graph.add_conditional_edges('evaluate',research_conditional,{
        'search' : 'search',
        'write': 'write'
    })
    research_graph.add_edge('write',END)
    
    memory = InMemorySaver()
    research = research_graph.compile(checkpointer = memory)
    
    result = research.invoke({
        'questions' : state['task'],
        'search_queries' : [],
        'iterations' : 3,
        "is_sufficient": False,
        "results": [],
        "final_answer": ""
    },config={'configurable':{'thread_id' : 'user1'}})
    
    return {'result': result['final_answer']}



print("Evaluation complete. Check LangSmith dashboard.")

def SummariserNode(state: SupervisorState):
    response = llm.invoke(f"""Summarize this text into 5 clear bullet points.
    Text: {state['task']}""")
    
    return {'result': response.content}


def SupervisorNode(state: SupervisorState):
    task = state['task']
    
    response = llm.invoke(f"""Given this task, decide which agent to call.
    Reply with only one word: RESEARCH or SUMMARY.
    
    RESEARCH — if the task needs searching the web for information
    SUMMARY — if the task needs summarizing a given text
    
    Task: {task}""")
    
    decision = response.content.strip().lower()
    
    if 'research' in decision:
        return {'agent_to_call' :'research' }
    else :
        return {'agent_to_call' : 'summary'}
    
    
    
def route_to_agent(state: SupervisorState):
    return state['agent_to_call']


supervisor_graph = StateGraph(SupervisorState)

supervisor_graph.add_node('supervisor', SupervisorNode)
supervisor_graph.add_node('research', ResearchNode)
supervisor_graph.add_node('summary', SummariserNode)

supervisor_graph.set_entry_point('supervisor')
supervisor_graph.add_conditional_edges('supervisor', route_to_agent, {
    'research':'research',
    'summary' :'summary'
})

supervisor_graph.add_edge('research',END)
supervisor_graph.add_edge('summary',END)

app = supervisor_graph.compile()

while True:
    
    user_input = input('You : ')
    
    if user_input.lower()=='exit':
        break
    result = app.invoke({
        'task' : user_input,
        'agent_to_call' : '',
        'result' : ''
    })
    print(f"\nBot : {result['result']}\n")
    
# res1 = app.invoke({
#     'task' : 'What is the advancement in quantam computing',
#     'agent_to_call' : '',
#     'result':''
# })
# print("Research result:\n", res1["result"][:500])


# res2 = app.invoke({
#     'task' : """Artificial intelligence is transforming every industry. 
#     From healthcare to finance, AI systems are making decisions that 
#     were once reserved for humans. While this brings enormous efficiency 
#     gains, it also raises serious concerns about job displacement and 
#     algorithmic bias that society must address urgently.""",
#     'agent_to_call' : '',
#     'result': ''
# })
# print("\nSummary result:\n", res2["result"])


# def research_agent(inputs: dict) -> dict:
#     result = app.invoke({
#         "task": inputs["question"],
#         "agent_to_call": "",
#         "result": ""
#     })
#     return {"result": result["result"]}

# def LLMJudge(run,example):
#     # print("run.outputs keys:", run.outputs)
#     question = example.inputs['question']
#     correct_ans = example.outputs['answer']
#     agent_ans = run.outputs['result']
    
#     response = llm.invoke(f"""Score this answer 1-5.
#     Question: {question}
#     Correct: {correct_ans}
#     Agent answer: {agent_ans}
#     Reply with only a number.""")
    
#     try:
#         score = int(response.content.strip()[0])
#     except:
#         score = 3
    
#     return {"key": "accuracy", "score": score}


# results = evaluate(
#     research_agent,
#     data="research-eval",
#     evaluators=[LLMJudge],
#     experiment_prefix="v1"
# )