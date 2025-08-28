from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Telegram Bot Configuration
    telegram_token: str = Field(default="", description="Telegram bot token")
    
    # API Configuration
    base_url: str = Field(default="https://yourvoice.sy/api", description="API base URL")
    image_base_url: str = Field(default="https://yourvoice.sy/", description="Image base URL")
    
    # Mobile Configuration
    country_code: str = Field(default="963", description="Country code")
    username_hint: str = Field(default="## ### ####", description="Username hint format")
    mobile_length: int = Field(default=8, description="Mobile number length")
    mobile_code: str = Field(default="09", description="Mobile code prefix")
    
    # Cache Configuration
    cache_expiry: int = Field(default=3600, description="Cache expiry time in seconds")
    
    # Logging Configuration
    log_format: str = Field(default='%(asctime)s - %(name)s - %(levelname)s - %(message)s', description="Log format")
    log_level: str = Field(default="INFO", description="Log level")
    
    # Form Validation
    max_description_length: int = Field(default=1000, description="Maximum description length")
    min_description_length: int = Field(default=10, description="Minimum description length")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings()
