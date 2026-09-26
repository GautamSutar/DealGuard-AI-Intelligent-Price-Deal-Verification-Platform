from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    app_cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://dealguard:dealguard_secret@localhost:5432/dealguard"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # AI / LLM
    # Provider: 'grok' (xAI) or 'groq' (Groq inference)
    llm_provider: str = "grok"

    # Grok / xAI  (https://x.ai)
    grok_api_key: str = ""
    grok_model: str = "grok-3"

    # Groq inference (fallback / alternative)
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"

    # Marketplace providers
    amazon_provider: str = "mock"
    keepa_api_key: str = ""
    flipkart_provider: str = "mock"
    flipkart_api_key: str = ""

    # ReefAPI (Flipkart + 293 other APIs — 1,000 free credits)
    reefapi_key: str = ""

    # QuickCommerceAPI (Blinkit, Zepto, Swiggy Instamart, BigBasket Now)
    quickcommerce_api_key: str = ""
    # Default delivery location — Bangalore Koramangala; override per request
    quickcommerce_default_lat: float = 12.9352
    quickcommerce_default_lon: float = 77.6245

    # RapidAPI (Amazon product data — free tier available)
    rapidapi_key: str = ""
    # Host depends on which RapidAPI Amazon service you subscribed to.
    # Common options:
    #   real-time-amazon-data.p.rapidapi.com
    #   amazon-product-data6.p.rapidapi.com
    #   axesso-amazon-data-service.p.rapidapi.com
    rapidapi_amazon_host: str = "real-time-amazon-data.p.rapidapi.com"
    rapidapi_amazon_country: str = "IN"

    # Price collection
    price_collection_interval_hours: int = 6
    price_cache_ttl_seconds: int = 900

    # Rate limiting
    provider_rate_limit_per_minute: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.app_cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
