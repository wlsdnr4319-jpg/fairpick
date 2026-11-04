#!/bin/sh
# 배포 순서를 스크립트로 고정한다 (레퍼런스 14장 운영 체크리스트):
#   코드 받기 → 이미지 빌드 → DB 마이그레이션 → 컨테이너 재시작 → 헬스 체크
# 서버의 저장소 폴더에서 실행: sh deploy/deploy.sh
set -eu

COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env"

echo "[1/5] git pull"
git pull --ff-only

echo "[2/5] build"
$COMPOSE build api nginx

echo "[3/5] db up + alembic upgrade head"
$COMPOSE up -d db
$COMPOSE run --rm api alembic upgrade head

echo "[4/5] restart"
$COMPOSE up -d api worker nginx

echo "[5/5] health check"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -fsS "http://localhost:${HTTP_PORT:-80}/api/v1/health?db=true" >/dev/null 2>&1; then
    echo "ok"
    exit 0
  fi
  sleep 3
done
echo "health check failed" >&2
$COMPOSE logs --tail=50 api >&2
exit 1
