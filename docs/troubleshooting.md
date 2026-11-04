# 트러블슈팅 기록

개발하면서 실제로 겪은 문제를 증상 → 원인 → 해결 → 배운 점 순서로 적었습니다.

## 1. Windows 에서만 상세 API 가 500 에러

- **증상:** 일시(`prereg_end_at`, `verified_at`)가 있는 박람회만 500. 리눅스(Docker 이미지)에서는 생기지 않는 문제다.
- **원인:** `zoneinfo.ZoneInfo("Asia/Seoul")` 이 `ZoneInfoNotFoundError`. 리눅스는 OS 의 시간대 DB(`/usr/share/zoneinfo`)를 쓰지만 Windows 에는 없다.
- **해결:** `tzdata` 패키지를 의존성에 추가.
- **배운 점:** "내 PC 에서만" 생기는 에러는 OS 차이를 먼저 의심한다. 500 응답에는 원인을 숨기므로(보안), `raise_server_exceptions=True` 로 테스트를 다시 돌려 원인을 찾았다.

## 2. `alembic` 명령이 `UnicodeDecodeError: 'cp949'`

- **증상:** `alembic.ini` 에 한글 주석을 넣자 모든 alembic 명령이 실패.
- **원인:** Alembic 이 ini 파일을 OS 기본 인코딩으로 읽는다. 한국어 Windows 는 cp949.
- **해결:** `alembic.ini` 는 ASCII 로만 작성하고, 설명은 `env.py` 에 적었다.

## 3. 개발 DB 컨테이너가 뜨지 않음 (3306 포트)

- **증상:** `ports are not available: ... 0.0.0.0:3306 ... Only one usage of each socket address`
- **원인:** PC 에 설치된 MySQL80 서비스가 3306 을 쓰고 있었다. 처음 포트를 확인할 때 한글 Windows 의 `netstat` 은 `LISTENING` 대신 `수신 대기` 로 출력해 검색에 걸리지 않았다.
- **해결:** 개발용 컨테이너는 호스트 포트 3308 을 기본값으로 쓴다 (`DB_PORT` 로 변경 가능). 포트 확인은 `Get-NetTCPConnection -State Listen` 으로.

## 4. Nginx 보안 헤더가 페이지마다 다르게 붙음

- **증상:** `X-Frame-Options`, `X-Content-Type-Options` 가 API 응답에는 있는데 HTML·정적 파일에는 없다.
- **원인:** Nginx 는 `location` 블록 안에 `add_header` 가 하나라도 있으면 `server` 블록의 `add_header` 를 **전혀** 물려받지 않는다. `location /` 에 `add_header Cache-Control ...` 를 넣은 것이 원인.
- **해결:** location 의 캐시 설정을 `expires` 지시어로 바꿔 `add_header` 를 없앴다. 운영 구성을 로컬에서 띄워 `curl -I` 로 확인.

## 5. 전문 검색 테스트만 결과가 0건

- **증상:** `LIKE` 를 ngram FULLTEXT 로 바꾸자 검색 테스트가 실패. 개발 DB 에서 직접 검색하면 잘 된다.
- **원인:** InnoDB FULLTEXT 인덱스는 **커밋된 행만** 반영한다. 테스트는 각자 롤백되는 트랜잭션 안에서 데이터를 만들기 때문에 인덱스에 들어가지 않았다.
- **해결:** 전문 검색 테스트는 데이터를 실제로 커밋하고, 끝나면 지우는 fixture 를 따로 만들었다. 한 글자 검색어는 ngram 토큰(2글자)보다 짧아 `LIKE` 로 처리.

## 6. 로그인이 이유 없이 풀릴 수 있음 (설계 단계에서 발견)

- **증상(예상):** 새로고침 직후 또는 여러 요청이 동시에 만료되면 로그아웃된다.
- **원인:** 리프레시 토큰은 쓸 때마다 새로 발급하고, 폐기된 토큰이 다시 오면 탈취로 보고 전부 폐기한다. React StrictMode 는 개발 중 effect 를 두 번 실행하므로 `/auth/refresh` 가 같은 토큰으로 두 번 나가고, 두 번째 요청이 '재사용'으로 탐지된다.
- **해결:** 재발급 요청을 모듈 단위 Promise 하나로 묶었다(single-flight). 앱 시작 복구와 401 재시도가 같은 함수를 쓴다.

## 7. 기간 정규화의 '해 넘김' 규칙이 잘못된 입력도 통과

- **증상:** `"2026.11.22 ~ 2026.11.19"` 가 2026-11-22 ~ 2027-11-19 로 해석됐다.
- **원인:** "끝이 시작보다 빠르면 끝 연도 +1" 규칙을 끝 연도를 명시한 경우에도 적용했다.
- **해결:** 끝 연도를 생략했을 때(`"12.30 ~ 1.2"`)만 해 넘김으로 본다. 실패 케이스를 단위 테스트로 추가.

## 8. 킨텍스 홀 이름에 줄바꿈이 섞임

- **증상:** 장소가 `"킨텍스 전시홀 6C\n\t\t ,\n 전시홀 7"` 처럼 저장될 뻔했다.
- **원인:** 목록 HTML 이 홀마다 줄바꿈과 들여쓰기를 넣는다.
- **해결:** 공통 `clean_text()` 로 공백을 한 칸으로 줄이고 쉼표 앞 공백을 지운다. 저장한 HTML fixture 로 파서를 테스트해 재발을 막는다.

## 9. 분석 차트의 한글·가운뎃점이 깨짐

- **증상:** matplotlib 차트의 한글이 네모로, '문화·예술' 의 '·' 이 빈칸으로 나온다.
- **원인:** 기본 폰트에 한글이 없고, 맑은 고딕에는 가운뎃점(U+00B7) 글자가 없다.
- **해결:** `font.family = "Malgun Gothic"` 지정, 표시용 이름의 '·' 을 한글 가운뎃점 'ㆍ'(U+318D)로 바꿨다.

## 10. IP 기준 로그인 제한을 헤더 하나로 피할 수 있었음 (구현 중 발견)

- **증상(예상):** 공격자가 요청마다 `X-Forwarded-For: 1.2.3.<n>` 을 바꿔 보내면 IP 당 실패 횟수 제한에 걸리지 않는다.
- **원인:** Nginx 가 `$proxy_add_x_forwarded_for` 로 클라이언트가 보낸 값 뒤에 실제 IP 를 *덧붙였고*, uvicorn 은 `--forwarded-allow-ips "*"` 라 목록의 맨 앞(클라이언트가 쓴 값)을 접속 IP 로 썼다.
- **해결:** Nginx 가 맨 앞단이므로 `proxy_set_header X-Forwarded-For $remote_addr;` 로 덮어쓴다. 추가로 Nginx `limit_req` 로 인증 API 를 IP 당 분당 30회(순간 20회)로 제한하고, 넘으면 앱과 같은 JSON 에러 형식으로 429 를 준다. `nginx -t` 와 실제 요청으로 429 를 확인했다.
