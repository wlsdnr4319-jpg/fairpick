#!/bin/sh
# 매일 mysqldump 로 백업하고 7일치를 보관한다 (레퍼런스 14장).
# 서버 crontab 예: 0 3 * * * cd /srv/fairpick && sh deploy/backup.sh >> /var/log/fairpick-backup.log 2>&1
# 백업은 서버 밖(스냅샷, 오브젝트 스토리지)에도 복사해 둔다 (15장).
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
mkdir -p "$BACKUP_DIR"

FILE="$BACKUP_DIR/fairpick-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose -f docker-compose.prod.yml --env-file .env exec -T db \
  sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --default-character-set=utf8mb4 fairpick' \
  | gzip > "$FILE"

echo "backup: $FILE ($(du -h "$FILE" | cut -f1))"
find "$BACKUP_DIR" -name 'fairpick-*.sql.gz' -mtime +"$KEEP_DAYS" -delete

# 관리자가 올린 표지 이미지 (api 컨테이너의 /app/uploads 볼륨)
IMG="$BACKUP_DIR/uploads-$(date +%Y%m%d-%H%M%S).tar.gz"
docker compose -f docker-compose.prod.yml --env-file .env exec -T api tar -czf - -C /app uploads > "$IMG"
echo "backup: $IMG ($(du -h "$IMG" | cut -f1))"
find "$BACKUP_DIR" -name 'uploads-*.tar.gz' -mtime +"$KEEP_DAYS" -delete

# 복구 리허설:
#   gunzip -c backups/fairpick-YYYYMMDD-HHMMSS.sql.gz | \
#     docker compose -f docker-compose.prod.yml exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" fairpick'
