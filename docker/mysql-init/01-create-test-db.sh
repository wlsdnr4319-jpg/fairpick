#!/bin/sh
# MySQL 컨테이너를 처음 만들 때(빈 볼륨) 한 번만 실행된다.
# 통합 테스트용 DB(fairpick_test)와 E2E 용 DB(fairpick_e2e)를 만들고 앱 계정에 권한을 준다 (레퍼런스 13장: 테스트 DB 는 Docker MySQL).
# 이미 만든 컨테이너에는 실행되지 않으니 docs/testing.md 의 명령으로 직접 만든다.
set -e

mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<SQL
CREATE DATABASE IF NOT EXISTS fairpick_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON fairpick_test.* TO '$MYSQL_USER'@'%';
CREATE DATABASE IF NOT EXISTS fairpick_e2e CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON fairpick_e2e.* TO '$MYSQL_USER'@'%';
FLUSH PRIVILEGES;
SQL
