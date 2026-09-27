"""Central configuration — env-based, no secrets in code."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./foodmate.db"
    JWT_SECRET: str = "foodmate-dev-secret-change-in-production"
    JWT_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    AI_PROVIDER: str = "rule"  # rule | openai | anthropic | gemini | local
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEMO_MODE: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
