from pydantic_settings import BaseSettings

class Setting(BaseSettings):
    groq_api_key: str
    redis_port:int
    redis_host:str
    db_path:str

    class Config():
        env_file= ".env"
        extra= "ignore"

settings = Setting()