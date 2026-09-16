from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Resolve .env from the repository root instead of the process working
    # directory. This keeps configuration loading stable in Jupyter notebooks,
    # whose kernels may start from a different directory.
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    fmp_api_key: str = ""
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    openbb_pat: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Optional China-market factor data provider.  The API URL is configurable
    # because some Tushare Pro subscriptions are accessed through a compatible
    # gateway rather than the default Tushare endpoint.
    tushare_token: str = ""
    tushare_api_url: str = ""

    fmp_base_url: str = "https://financialmodelingprep.com/stable"
    cache_ttl_seconds: int = 86400  # 24 hours
    agent_memory_turns: int = 20    # sliding-window size; set AGENT_MEMORY_TURNS in .env


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
