from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 설정. 값은 저장소 루트의 .env 에서 읽는다 (레퍼런스 14장 환경 변수)."""

    # backend/ 에서 실행하면 ../.env, 루트에서 실행하면 .env 를 읽는다
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "mysql+pymysql://fairpick:change-me@localhost:3308/fairpick?charset=utf8mb4"

    jwt_secret: str = "dev-only-secret-change-me"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    # 운영(HTTPS)에서는 true. 개발 서버(http://localhost)에서는 Secure 쿠키가 저장되지 않아 false
    cookie_secure: bool = False

    app_tz: str = "Asia/Seoul"

    # 쉼표로 여러 개: http://localhost:5173,http://127.0.0.1:5173
    cors_origins: str = Field(default="http://localhost:5173")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
