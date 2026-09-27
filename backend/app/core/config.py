"""Central configuration — env-based, no secrets in code."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./foodmate.db"
    JWT_SECRET: str = "foodmate-dev-secret-change-in-production"
    JWT_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"  # covers production + preview deployments
    AI_PROVIDER: str = "rule"  # rule | openai | anthropic | gemini | openrouter
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    AI_MODEL: str = ""  # override model for active provider; openrouter default is Nemotron free
    AI_RATE_LIMIT_PER_HOUR: int = 40  # per-user AI chat cap (protects free-model quota)
    DEMO_MODE: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
