from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BACKEND_DIR / "fixtures"


class Settings(BaseSettings):
    """Runtime configuration. Everything secret comes from the environment (backend/.env)."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # "bedrock"   Claude via Amazon Bedrock (AWS credentials or a Bedrock API key)
    # "anthropic" Claude via the Anthropic API (ANTHROPIC_API_KEY)
    # "mock"      same pipeline, deterministic heuristics, no model calls
    provider: str = "bedrock"

    # Bedrock
    aws_region: str = "us-west-2"
    aws_bearer_token_bedrock: str | None = None   # Bedrock API key (bearer token). Or set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY.
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None
    bedrock_model: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    # Anthropic API
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    # Optional. Without these the SMS adapter logs outbound messages instead of sending.
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    database_path: Path = BACKEND_DIR / "tabbed.db"
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def bedrock_configured(self) -> bool:
        import os
        return bool(self.aws_bearer_token_bedrock or os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
                    or (self.aws_access_key_id and self.aws_secret_access_key)
                    or os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE")
                    or (Path.home() / ".aws" / "credentials").exists())

    @property
    def llm_enabled(self) -> bool:
        if self.provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.provider == "bedrock":
            return self.bedrock_configured
        return False

    @property
    def model_label(self) -> str:
        return self.bedrock_model if self.provider == "bedrock" else self.anthropic_model


settings = Settings()
