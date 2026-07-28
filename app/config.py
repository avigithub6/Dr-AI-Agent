from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str

    HOST: str
    PORT: int

    DEBUG: bool

    class Config:
        env_file =".env"


settings = Settings()        