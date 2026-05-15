"""
Concepts covered:
1. PromptTemplat
2. LLM Wrappers
3. Output parsers
4. Runnables / LCEL Chain
5. Callbacks
6. Cache
"""
# from langchain.globals import set_llm_cache --- another thing 


from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
# from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from langchain_huggingface import HuggingFaceEndpoint   # did not work some model issue 

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from langchain_core.exceptions import OutputParserException

from langchain_community.cache import InMemoryCache
from langchain_core.callbacks import BaseCallbackHandler
import langchain

import time


langchain.llm_cache = InMemoryCache()
print("IN - Memory Cache set up....")


class Recipe(BaseModel):
    name : str
    ingredients : List[str]
    steps : List[str]
    cook_time : int
    calories : int
    difficulty : str
    
    
parser = PydanticOutputParser(pydantic_object = Recipe)
print("Pydantic Output Parser set up....")
print(parser.get_format_instructions())


template = '''
    You are a professional chef AI. Create a creative delicious recipe based on the ingredients below.
    
    Dietary Preferences : {dietary_pref}
    Available Ingredients : {ingredients}
    
    Rules :
    - You MUST use at least 3 of the provided ingredients in the recipe.
    - The recipe must respect the dietary preferences specified.
    - Be creative but realistic.
    - The recipe should be delicious and appealing.
    - Provide a name for the recipe.
    - Include a list of ingredients with quantities.
    
    {format_instructions}
'''

prompt = PromptTemplate(
    template=template,
    input_variables=["ingredients", "dietary_pref"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)
 
print("Chat Prompt Template set up....")

class RecipeCallback(BaseCallbackHandler):
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        print("LLM started....")
        self._start_time = time.time()
    
    def on_llm_error(self, error, **kwargs):
        print(f"LLM error occurred: {repr(error)}")
    
    def on_llm_end(self, response, **kwargs):
        end = time.time() - self._start_time
        print(f"LLM finished in {end} seconds....")
        tokens = response.llm_output.get("token_usage",{}) if response.llm_output else {}
        if tokens:
            print(f"prompt : {tokens.get('prompt_tokens',0)}")
            print(f"completion : {tokens.get('completion_tokens',0)}")
            
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.7,
    callbacks=[RecipeCallback()]
)
print("Hugging Face Endpoint set up....")


chain = prompt | llm | parser
print("Chain set up....")


def generate_recipe(dietary_pref :str, ingredients: str) ->Recipe |None:
    print("Generating recipe....")
    
    try:
        recipe : Recipe = chain.invoke({"dietary_pref": dietary_pref, "ingredients": ingredients})
        return recipe
    
    except OutputParserException as e:
        print("Output parsing failed....")
        print(e)
        return None
    
    except Exception as e:
        print("An error occurred while generating the recipe....")
        print(e)
        return None
    
    
def print_rec(recipe:Recipe):
    if recipe:
        print(f"\n{'-'*30}")
        print(f"{recipe.name}")
        print(f"{'-'*15}")
        print(f"Cook Time : {recipe.cook_time} minutes")
        print(f"Calories : {recipe.calories} kcal")
        print(f"Difficulty : {recipe.difficulty}")
        print(f"\nIngredients :")
        for ingre in recipe.ingredients :
            print(f"    - {ingre}")
        
        print(f"\nSteps :")
        for i,step in enumerate(recipe.steps,1):
            print(f"    {i}. {step}")
            
        print(f"{'-'*30}\n")
    else :
        print("No recipe to display....")
        
        
        
if __name__ == "__main__":
    
    print("Welcome to the Recipe Generator!")
    
    recipe1 = generate_recipe(
        ingredients = "chicken, garlic, onion, tomato, basil, olive oil",
        dietary_pref = "non-vegetarian"
    )
    
    if recipe1:
        print_rec(recipe1)

    print("using cache")
    t0= time.time()
    recipe2 = generate_recipe(
        ingredients = "chicken, garlic, onion, tomato, basil, olive oil",
        dietary_pref = "non-vegetarian"
    )
    t1 = time.time()
    print(f"Time with cache : {t1-t0} seconds")
    
    