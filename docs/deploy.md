# 배포 가이드

클라우드 서버 한 대에 Docker Compose 로 Nginx, API, 워커, MySQL 을 함께 띄운다 (설계 레퍼런스 14장).
프론트 빌드 결과도 같은 Nginx 가 서빙해 프론트와 API 가 한 도메인이 된다. 그래서 쿠키·CORS 문제가 없다.

```
브라우저 ──HTTPS──▶ nginx ──/api/──▶ api (uvicorn, 워커 2개) ──▶ db (MySQL 8.4, 외부 포트 없음)
                     └── 그 외 ──▶ React 빌드 파일            worker (수집 04:00, 알림 09:00 KST) ──▶ db
```

## 1. 서버 준비 (사용자가 직접)

| 항목 | 내용 |
| --- | --- |
| 서버 | 권장: Amazon Lightsail 2GB 서울 리전 (월 $12). 무료: Oracle Cloud Always Free Arm VM (홈 리전 서울, 유휴 회수 주의) |
| 도메인 | 가비아 등에서 구입 후 A 레코드를 서버 IP 로 |
| 방화벽 | 80, 443 만 전체 허용. 22 는 내 IP 만. 3306 은 열지 않는다 |
| SSH | 키 로그인만 허용, 비밀번호 로그인 끄기 |
| OS 업데이트 | `sudo apt install unattended-upgrades` |
| Docker | `curl -fsSL https://get.docker.com \| sh` 후 `sudo usermod -aG docker $USER` |

Arm 서버(Oracle)는 `mysql:8.4`, `python:3.13-slim`, `node:22-alpine`, `nginx:stable-alpine` 모두 arm64 를 지원한다.

## 2. 처음 배포

```sh
git clone https://github.com/wlsdnr4319-jpg/fairpick.git /srv/fairpick
cd /srv/fairpick
cp .env.example .env
vi .env
```

`.env` 에서 반드시 바꿀 값:

| 변수 | 값 |
| --- | --- |
| `DB_PASSWORD`, `DB_ROOT_PASSWORD` | `openssl rand -base64 24` |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `COOKIE_SECURE` | `true` (HTTPS 에서만 로그인 쿠키 전송) |
| `CORS_ORIGINS` | 비워 둬도 됨 (같은 도메인) |
| `CRAWL_USER_AGENT` | `FairPickBot/1.0 (+실제 연락 이메일)` |

`DATABASE_URL` 은 compose 가 컨테이너용(`@db:3306`)으로 덮어쓰므로 그대로 둬도 된다.

```sh
sh deploy/deploy.sh                                  # 빌드 → 마이그레이션 → 실행 → 헬스 체크
docker compose -f docker-compose.prod.yml run --rm api python -m app.scripts.seed          # 시드 (처음 한 번)
docker compose -f docker-compose.prod.yml run --rm api python -m app.scripts.create_admin --email 내이메일
```

## 3. HTTPS (Let's Encrypt)

```sh
# 1) HTTP 로 떠 있는 상태에서 인증서 발급 (webroot)
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot -d example.com --email 내이메일 --agree-tos --no-eff-email

# 2) deploy/nginx.https.conf 의 example.com 을 실제 도메인으로 바꾸고,
#    docker-compose.prod.yml 의 nginx volumes 에서 nginx.https.conf 줄의 주석을 푼다
docker compose -f docker-compose.prod.yml up -d nginx

# 3) 자동 갱신 (crontab -e)
0 4 * * 1 cd /srv/fairpick && docker compose -f docker-compose.prod.yml run --rm certbot renew -q && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## 4. 운영

| 할 일 | 명령 |
| --- | --- |
| 다시 배포 | `sh deploy/deploy.sh` |
| 로그 | `docker compose -f docker-compose.prod.yml logs -f api worker` |
| 수동 수집 | `docker compose -f docker-compose.prod.yml exec worker python -m app.jobs.crawl_job` |
| 백업 (매일 03:00) | crontab: `0 3 * * * cd /srv/fairpick && sh deploy/backup.sh` — 7일치 보관. 서버 밖에도 복사 |
| 복구 리허설 | `deploy/backup.sh` 맨 아래 주석 참고. 한 번은 꼭 해 본다 |
| 업타임 모니터링 | `https://도메인/api/v1/health` 를 5분마다 확인 (무료 모니터링 서비스) |

스키마 변경은 Alembic 으로만 한다. 운영 DB 에 직접 ALTER 하지 않는다. `deploy.sh` 가 `alembic upgrade head` 를 실행한다.

## 5. 공개 전 체크리스트 (레퍼런스 15장)

- [ ] `frontend/src/pages/Legal.jsx` 의 연락 이메일·시행일을 실제 값으로 바꾸기 (법률 전문가 검토 권장)
- [ ] 푸터의 `contact@example.com` 바꾸기 (`frontend/src/components/Layout.jsx`)
- [ ] `COOKIE_SECURE=true`, HTTPS 적용
- [ ] 관리자 계정 만들기, 시드 박람회 정보 공식 사이트에서 다시 확인
- [ ] 메일 발송을 켤 때: 발신 도메인 SPF·DKIM·DMARC, 처리방침에 위탁 업체·국외 이전 추가
- [ ] 백업·복구 리허설, 업타임 모니터링
- [ ] 방문 통계(GA4 등)를 붙이면 처리방침의 쿠키 항목에 반영
