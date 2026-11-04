"""공통 의존성. 테스트에서 app.dependency_overrides 로 바꿔 끼울 수 있다."""

from datetime import date

from app.core.timeutil import today_kst


def get_today() -> date:
    """
    오늘(한국 시간). 시간에 따라 결과가 바뀌는 로직은 today 를 인자로 받아,
    테스트에서 날짜를 고정할 수 있게 한다 (레퍼런스 13장 테스트 환경).
    """
    return today_kst()
