# 페어픽 API·워커 이미지 (레퍼런스 14장). docker-compose.prod.yml 의 api, worker 서비스가 같은 이미지를 쓴다.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# root 가 아닌 사용자로 실행한다
RUN useradd --create-home --uid 1000 fairpick
USER fairpick

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
