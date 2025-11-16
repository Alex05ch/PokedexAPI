from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./pokemon.db"

    # Security
    secret_key: str = "1234"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list[str] = ["*"]

    # Rate Limiting
    rate_limit: str = "100/minute"

    class Config:
        env_file = ".env"

settings = Settings()
