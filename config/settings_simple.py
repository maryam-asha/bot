import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Simple application settings without external dependencies"""
    
    def __init__(self):
        # Telegram Bot Configuration
        self.telegram_token = os.getenv("TELEGRAM_TOKEN", "")
        
        # API Configuration
        self.base_url = os.getenv("BASE_URL", "https://yourvoice.sy/api")
        self.image_base_url = os.getenv("IMAGE_BASE_URL", "https://yourvoice.sy/")
        
        # Mobile Configuration
        self.country_code = os.getenv("COUNTRY_CODE", "963")
        self.username_hint = os.getenv("USERNAME_HINT", "## ### ####")
        self.mobile_length = int(os.getenv("MOBILE_LENGTH", "8"))
        self.mobile_code = os.getenv("MOBILE_CODE", "09")
        
        # Cache Configuration
        self.cache_expiry = int(os.getenv("CACHE_EXPIRY", "3600"))
        
        # Logging Configuration
        self.log_format = os.getenv("LOG_FORMAT", '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Form Validation
        self.max_description_length = int(os.getenv("MAX_DESCRIPTION_LENGTH", "1000"))
        self.min_description_length = int(os.getenv("MIN_DESCRIPTION_LENGTH", "10"))
    
    def validate(self):
        """Basic validation of required settings"""
        if not self.telegram_token:
            raise ValueError("TELEGRAM_TOKEN is required")
        
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError("BASE_URL must be a valid HTTP/HTTPS URL")
        
        if not self.image_base_url.startswith(('http://', 'https://')):
            raise ValueError("IMAGE_BASE_URL must be a valid HTTP/HTTPS URL")

# Global settings instance
settings = Settings()

# Validate settings on import
try:
    settings.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    # You can set a default token here for development
    # settings.telegram_token = "your_default_token_here"
