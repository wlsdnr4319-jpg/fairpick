"""
수집용 HTTP 클라이언트. 수집 매너를 한곳에서 지킨다 (레퍼런스 8장 '수집 매너와 안정성').

- User-Agent 에 서비스 이름과 연락 이메일을 적는다
- 요청 사이에 2초 이상 쉰다
- 타임아웃 10초, 실패하면 간격을 늘려 가며 3번까지 다시 시도한다
"""

import logging
import time

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FetchError(Exception):
    pass


class PoliteClient:
    def __init__(self, *, delay: float = 2.0, retries: int = 3, timeout: float = 10.0, sleep=time.sleep):
        self.delay = delay
        self.retries = retries
        self.sleep = sleep
        self._last_request = 0.0
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": get_settings().crawl_user_agent, "Accept-Language": "ko-KR,ko;q=0.9"},
        )

    def get(self, url: str, params: dict | None = None) -> str:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            wait = self.delay - (time.monotonic() - self._last_request)
            if wait > 0:
                self.sleep(wait)
            try:
                self._last_request = time.monotonic()
                res = self._client.get(url, params=params)
                if res.status_code >= 500 or res.status_code == 429:
                    raise FetchError(f"HTTP {res.status_code}")
                res.raise_for_status()
                return res.text
            except (httpx.HTTPError, FetchError) as exc:
                last_error = exc
                logger.warning("fetch failed (%s/%s) %s: %s", attempt, self.retries, url, exc)
                if attempt < self.retries:
                    self.sleep(self.delay * 2**attempt)  # 4초, 8초 …
        raise FetchError(f"{url}: {last_error}")

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
