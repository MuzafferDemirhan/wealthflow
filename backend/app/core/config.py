from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "WealthFlow"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database — MS SQL Server 2022
    # Format: mssql+pyodbc://user:password@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server
    DATABASE_URL: str = (
        "mssql+pyodbc://sa:YourPassword@localhost:1433/wealthflow"
        "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Plaid
    PLAID_CLIENT_ID: str = ""
    PLAID_SECRET: str = ""
    PLAID_ENV: str = "sandbox"

    # Anthropic
    CLAUDE_API_KEY: str = ""

    # Market data
    ALPHA_VANTAGE_KEY: str = ""


settings = Settings()
