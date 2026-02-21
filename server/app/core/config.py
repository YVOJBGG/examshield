from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "ExamShield"
    ENV: str = "dev"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"


settings = Settings()
