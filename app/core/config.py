from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "VoxTask API"
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_a_long_random_string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    DATABASE_URL: str = "sqlite:///./voxtask.db"

    # If set, the NLP service calls the Anthropic API. If empty,
    # it falls back to a local rule-based parser (works offline / no key).
    ANTHROPIC_API_KEY: str = ""
    NLP_MODEL: str = "claude-sonnet-4-6"

    # Comma-separated list of allowed CORS origins ("*" for any).
    CORS_ORIGINS: str = "*"

    class Config:
        env_file = ".env"

    @property
    def sqlalchemy_url(self) -> str:
        """Render/Railway hand out 'postgres://' URLs, but SQLAlchemy needs
        'postgresql://'. Normalize so the same code runs locally and hosted."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()
