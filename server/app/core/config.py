from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "ExamShield"
    ENV: str = "dev"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    DATABASE_URL: str = "postgresql+psycopg://examshield:examshield@localhost:5432/examshield"
    DATABASE_URL_TEST: str | None = None
    JWT_SECRET_KEY: str = "change-me-in-dev"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
