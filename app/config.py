"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    app_name: str = "Dementia Research and Treatments Information"
    app_version: str = "1.0.0"
    cache_ttl: int = 3600
    supported_languages: str = "en,de,fr,es,it,hr"
    
    @property
    def languages_list(self) -> List[str]:
        """Get list of supported languages."""
        return [lang.strip() for lang in self.supported_languages.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
