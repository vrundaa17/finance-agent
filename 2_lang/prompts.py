from langchain_core.prompts import PromptTemplate

template = """ 
You are a helpful assistant that helps generate a list of interview questions 
for the given job role, experience level and topics. 
The questions should be relevant to the job role and experience level, and should cover the specified topics.
The questions should be open-ended and should encourage the candidate to provide dtailed answers.
the question should be in list format and should be numbered. there should be 5 questions in total.
Here are the details:
Job Role : {role}
Experience Level : {experience_level}
Topics : {topics}
Please generate the interview questions based on the above details.
"""



role = input("role :")
experience_level = input("experience level :")
topics = input("topics :")

prompt = PromptTemplate(
    template = template,
    input_variables = ["role", "experience_level", "topics"]
)
print(prompt.format(role=role, experience_level=experience_level, topics=topics))


# another approach
prompt1= PromptTemplate.from_template(template)
print(prompt1.format(role=role, experience_level=experience_level, topics=topics))
# why from_template and not just PromptTemplate ?
# from_template is a class method that allows us to create a PromptTemplate instance from a template string.
# it is a convenient way to create a PromptTemplate instance without having to specify the input_variables
#  like this part  input_variables=["role", "experience_level", "topics"]
#       is not needed when using from_template because it can automatically extract the input variables from the template string.


# ChatPromptTemplate is a subclass of PromptTemplate that is specifically designed for chat-based applications. 
# It allows us to create prompts that are more conversational in nature, and it also provides additional
# features such as the ability to specify the role of the assistant and the user in the conversation.

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage


prompt3 = ChatPromptTemplate.from_messages([
    ("system", template),
    ("user", "help me ")
])
print(prompt3.format_messages(role=role, experience_level=experience_level, topics=topics))