from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BACKEND_DIR / "fixtures"


class Settings(BaseSettings):
    """Runtime configuration. Everything secret comes from the environment."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # "anthropic" uses Claude for receipt reading, matching and memos.
    # "mock" runs the same pipeline with deterministic heuristics, no API key needed.
    provider: str = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    # Optional. Without these the SMS adapter logs outbound messages instead of sending.
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    database_path: Path = BACKEND_DIR / "tabbed.db"
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def llm_enabled(self) -> bool:
        return self.provider == "anthropic" and bool(self.anthropic_api_key)


settings = Settings()
