import os
from dotenv import load_dotenv

# Load standard .env file if it exists
load_dotenv()

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-3.5-flash")
    PORT: int = int(os.getenv("PORT", "3000"))
    
    @property
    def is_api_key_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

settings = Settings()
