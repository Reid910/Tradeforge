from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Tradeforge API"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://tradeforge:tradeforge@localhost:5432/tradeforge"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    session_cookie_name: str = "tf_session"

    auth_rate_limit_attempts: int = 5
    auth_rate_limit_window_seconds: int = 60

    magic_link_expire_minutes: int = 15
    frontend_url: str = "http://localhost:3100"

    # Mine production tuning. Short cycles/caps on purpose - this is a portfolio
    # demo, not a real idle game, so progress should be visible within seconds.
    mine_base_cycle_seconds: int = 6
    mine_cycle_reduction_per_level: int = 1
    mine_min_cycle_seconds: int = 2
    mine_base_storage: int = 20
    mine_storage_per_level: int = 10
    mine_max_level: int = 10
    mine_max_offline_hours: int = 24

    @property
    def cookie_secure(self) -> bool:
        return self.environment == "production"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
