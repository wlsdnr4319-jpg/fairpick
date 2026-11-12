"""
거리 계산 ('내 주변 박람회').

정렬·반경 필터는 DB 의 ST_Distance_Sphere 로, 카드에 보여 줄 거리는 같은 공식으로 파이썬에서 계산한다.
두 값이 어긋나지 않도록 MySQL 기본값과 같은 지구 반지름을 쓴다.
"""

from math import asin, cos, radians, sin, sqrt

from sqlalchemy import func

EARTH_RADIUS_M = 6_370_986  # MySQL ST_Distance_Sphere 기본 반지름


def distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이의 대원 거리(km, 하버사인 공식)."""
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = p2 - p1, radians(lng2 - lng1)
    h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(h)) / 1000


def distance_m_sql(lat_col, lng_col, lat: float, lng: float):
    """SQL 식: 좌표 컬럼에서 (lat, lng) 까지의 거리(m). 좌표가 NULL 이면 NULL. POINT 는 (경도, 위도) 순서다."""
    return func.ST_Distance_Sphere(func.point(lng_col, lat_col), func.point(lng, lat))
