from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    
    ENVIRONMENT :str

    SENDGRID_FROM_EMAIL:str
    SENDGRID_API_KEY:str


    SENDGRID_API_KEY : str
    SENDGRID_FROM_EMAIL :str


    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_NAME: str

    GEMINI_API_KEY: str


    AES_SECRET_KEY:str

    RECAPTCHA_SECRET_KEY:str

    JWT_SECRET_KEY:str  
    JWT_ALGORITHM : str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES : int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS : int = 1    # 1 days


    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    GOOGLE_TOKEN_VERIFY_URL:str

    FRONTEND_URL: str




    @property
    def DATABASE_URL(self) -> str:
        """Generate PostgreSQL database URL"""
        return f"postgresql://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        

# Create settings instance
settings = Settings()
