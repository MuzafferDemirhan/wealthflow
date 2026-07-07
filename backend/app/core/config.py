import json
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "WealthFlow"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database - MS SQL Server 2022
    # Format: mssql+pyodbc://user:password@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server
    DATABASE_URL: str = (
        "mssql+pyodbc://sa:YourPassword@localhost:1433/wealthflow"
        "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Plaid (https://plaid.com)
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"
    PLAID_PRODUCTS: list[str] = ["transactions"]
    PLAID_COUNTRY_CODES: list[str] = ["US", "GB", "NL", "PL"]

    # Token encryption
    TOKEN_ENCRYPTION_KEY: str = ""

    # Export
    EXPORT_DIR: str = "exports"

    # LLM (OpenAI-compatible API — Groq, OpenRouter, etc.)
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Market data
    ALPHA_VANTAGE_KEY: str = ""

    @field_validator("PLAID_PRODUCTS", "PLAID_COUNTRY_CODES", "ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_list(cls, v: object) -> object:
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [x.strip() for x in v.split(",") if x.strip()]
        return v


settings = Settings()
