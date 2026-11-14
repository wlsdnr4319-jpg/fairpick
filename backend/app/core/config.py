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
    # 회전 직후 응답이 끊겨 새 쿠키를 못 받은 브라우저가 이전 토큰을 다시 보내도, 이 시간(초) 안이면 탈취로 보지 않는다
    refresh_reuse_grace_seconds: int = 30
    # 운영(HTTPS)에서는 true. 개발 서버(http://localhost)에서는 Secure 쿠키가 저장되지 않아 false
    cookie_secure: bool = False

    app_tz: str = "Asia/Seoul"

    # 쉼표로 여러 개: http://localhost:5173,http://127.0.0.1:5173
    cors_origins: str = Field(default="http://localhost:5173")

    # 수집 요청 식별 (레퍼런스 8장: User-Agent 에 서비스 이름과 연락 이메일)
    crawl_user_agent: str = "FairPickBot/1.0 (+contact@example.com)"

    # 메일 (2단계 알림). SMTP_HOST 가 비어 있으면 실제로 보내지 않고 로그로만 남긴다 (개발용)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    mail_from: str = "페어픽 <no-reply@example.com>"
    # 메일 속 링크의 기준 주소 (프론트 주소)
    app_base_url: str = "http://localhost:5173"

    # 소셜 로그인 (카카오·구글). 비어 있으면 그 로그인은 꺼진다 (버튼이 숨겨지고 시작 API 는 로그인 화면으로 돌려보냄)
    # 콘솔에 등록할 Redirect URI: {APP_BASE_URL}/api/v1/auth/oauth/{kakao|google}/callback
    kakao_client_id: str = ""  # REST API 키
    kakao_client_secret: str = ""  # 카카오 콘솔에서 Client Secret 을 켰을 때만
    google_client_id: str = ""
    google_client_secret: str = ""

    # 웹 푸시 (브라우저 알림). 비어 있으면 푸시가 꺼진다. 키 만들기: python -m app.scripts.gen_vapid
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:contact@example.com"  # 푸시 서비스가 문제 있을 때 연락할 주소

    # 관리자가 올린 박람회 표지 이미지 저장 폴더. 운영에서는 docker volume 으로 붙인다 (docker-compose.prod.yml)
    upload_dir: str = "uploads"
    upload_max_bytes: int = 5 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
