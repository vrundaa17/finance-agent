from pydantic_settings import BaseSettings
import os
class Setting(BaseSettings):
    groq_api_key: str
    redis_port:int
    redis_host:str
    db_path:str
    
    
    class Config():
        env_file= ".env"
        extra= "ignore"

settings = Setting()
PROJECT_ROOT= os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join("data","charts")