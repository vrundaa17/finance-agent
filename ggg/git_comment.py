from typing import TypedDict, Literal,List
from github import Github
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph,END
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel,Field
import os
from dotenv import load_dotenv
load_dotenv()

g= Github(os.getenv("GITHUB_TOKEN"))
llm = ChatGroq(model="llama-3.1-8b-instant")

def validate_in():
    
    return
class PRState(TypedDict):
    pr_url : str
    pr_diff : str
    pr_title : str
    review : str
    comment: str
    pr_desc : str
    repo_name : str
    pr_number : int
    
class Review(BaseModel):
    pr : List[str] = Field(description="Provide detail for What this PR does?")
    bugs : List[str] = Field(description="Provide detail for What are the Potential bugs or risks?")
    edge_case : List[str] = Field(description="Provide detail for What edge cases are not handled?")
    suggestion : List[str] = Field(description="Provide detail explanation for Suggestions for improvement")
    verdict : Literal['Approved','Rejected'] = Field(description="The verdict for the PR")
review_llm=llm.with_structured_output(Review)

def fetch_pr(state : PRState):
    #pr_url like: https://github.com/owner/repo/pull/123
    
    part = state['pr_url'].strip("/").split("/")
    repo_name = part[-4]+"/"+part[-3]
    pr_number = int(part[-1])
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    return {
        'repo_name' : repo_name,
        'pr_number' : pr_number,
        'pr_title': pr.title, 
        'pr_desc' : pr.body or "No description provided."}
    

def fetch_diff(state : PRState):
    
    repo = g.get_repo(state['repo_name'])
    pr = repo.get_pull(state['pr_number'])
    
    diff =''
    for file in pr.get_files():
        diff += f'\n---\nFile : {file.filename} \n'
        diff += file.patch or "No file"
    return {'pr_diff': diff[:500]}


def analyse(state : PRState):
    prompt = f"""You are a Chief Technology Officer and you are reviewing the pull request.
    PR Title {state['pr_title']}
    PR Description {state['pr_desc']}
    Code Changes : {state['pr_diff']}
    Provide in detail response. NOT just points.
    """
    
    review : Review = review_llm.invoke(prompt)
    comment = "Suggestions for improvement\n" + "\n".join(
        f"- {s}" for s in review.suggestion
    )
    return {
        'review' : review.model_dump_json(indent=2),
        'comment': comment
    }
     


def post_comment(state:PRState):

    repo = g.get_repo(state['repo_name'])
    pr = repo.get_pull(state['pr_number'])
    pr.create_issue_comment(state['comment'])        
    print('review posted...')

    return {}



graph = StateGraph(PRState)
graph.add_node('pr',fetch_pr)
graph.add_node('diff',fetch_diff)
graph.add_node('analyse',analyse)
graph.add_node('comment',post_comment)

#
graph.set_entry_point('pr')
graph.add_edge('pr','diff')
graph.add_edge('diff','analyse')
graph.add_edge('analyse','comment')
graph.add_edge('comment',END)

memory = InMemorySaver()
app = graph.compile(checkpointer = memory,interrupt_before=['comment'])
config = {"configurable": {"thread_id": "t1"}}
result = app.invoke(
    {'pr_url':'https://github.com/vrundaa17/dummy/pulls/1'},
    config = config
)
print(result['review'])
inu = input('Post?? y/n :')
if inu.lower() =='y':
    app.invoke(None,config=config)
else : 
    print("stopping... no posting...")
    
