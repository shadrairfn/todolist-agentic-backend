import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL"
    )
    AUTO_CREATE_TABLES: bool = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAY: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAY", 7))

    # Groq API Key (optional for other features, but good to have here if needed)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    AGENT_MAX_OUTPUT_TOKENS: int = int(os.getenv("AGENT_MAX_OUTPUT_TOKENS", 512))
    AGENT_RECENT_MESSAGE_LIMIT: int = int(os.getenv("AGENT_RECENT_MESSAGE_LIMIT", 2))
    AGENT_RECENT_TOOL_CALL_LIMIT: int = int(os.getenv("AGENT_RECENT_TOOL_CALL_LIMIT", 2))

settings = Settings()
