-- 페어픽(FairPick) 1단계(MVP) 테이블 12개
-- 설계 레퍼런스 6장 기준. 실제 DB 는 2주차부터 Alembic 마이그레이션으로 만든다.
-- 이 파일은 설계 확인·리뷰용이며, 운영 DB 에 직접 실행하지 않는다 (레퍼런스 14장 운영 체크리스트).
--
-- 원칙
--   - utf8mb4 / utf8mb4_0900_ai_ci: 한글과 이모지 저장
--   - 박람회 기간은 DATE, 그 외 일시는 DATETIME(UTC). 화면에서 한국 시간으로 바꾼다
--   - 진행 상태(예정·진행 중·종료)와 D-day 는 저장하지 않고 조회할 때 계산한다
--   - 고정된 상태 값은 ENUM, 관리자가 늘리는 분류(카테고리·태그)는 별도 테이블
--   - 모르는 값은 NULL. 입장료 미확인(NULL)과 무료(0)를 구분한다
--   - 박람회는 삭제하지 않고 status = 'hidden' 으로 숨긴다
--   - 회원 탈퇴 시 북마크·토큰은 ON DELETE CASCADE 로 함께 지운다

SET NAMES utf8mb4;

-- ---------------------------------------------------------------------------
-- 회원
-- ---------------------------------------------------------------------------

CREATE TABLE users (
    id             BIGINT        NOT NULL AUTO_INCREMENT,
    email          VARCHAR(255)  NOT NULL,
    password_hash  VARCHAR(255)  NOT NULL,               -- Argon2 해시 (pwdlib)
    nickname       VARCHAR(30)   NOT NULL,
    role           ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    created_at     DATETIME      NOT NULL,
    updated_at     DATETIME      NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE refresh_tokens (
    id          BIGINT    NOT NULL AUTO_INCREMENT,
    user_id     BIGINT    NOT NULL,
    token_hash  CHAR(64)  NOT NULL,                      -- SHA-256. 원문은 저장하지 않는다
    expires_at  DATETIME  NOT NULL,
    revoked_at  DATETIME  NULL,                          -- 회전·로그아웃 시 채운다
    created_at  DATETIME  NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_refresh_tokens_hash (token_hash),
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------------
-- 참조 데이터: 전시장, 카테고리, 태그
-- ---------------------------------------------------------------------------

CREATE TABLE venues (
    id            BIGINT         NOT NULL AUTO_INCREMENT,
    name          VARCHAR(100)   NOT NULL,               -- 예: 코엑스
    region        VARCHAR(20)    NOT NULL,               -- 시·도. 목록 필터(region=서울)에 쓴다
    address       VARCHAR(255)   NULL,                   -- 예: 서울 강남구 영동대로 513
    latitude      DECIMAL(10, 7) NULL,                   -- 3단계 지도
    longitude     DECIMAL(10, 7) NULL,
    parking_note  VARCHAR(500)   NULL,
    created_at    DATETIME       NOT NULL,
    updated_at    DATETIME       NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_venues_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 수집한 장소 문자열("COEX", "서울 코엑스")을 venue 로 맞추는 별칭
CREATE TABLE venue_aliases (
    id        BIGINT        NOT NULL AUTO_INCREMENT,
    venue_id  BIGINT        NOT NULL,
    alias     VARCHAR(100)  NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_venue_aliases_alias (alias),
    CONSTRAINT fk_venue_aliases_venue FOREIGN KEY (venue_id) REFERENCES venues (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE categories (
    id          INT          NOT NULL AUTO_INCREMENT,
    code        VARCHAR(30)  NOT NULL,                   -- food, culture, lifestyle, leisure, pet, family, tech
    name        VARCHAR(50)  NOT NULL,
    sort_order  INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_categories_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE tags (
    id          INT          NOT NULL AUTO_INCREMENT,
    name        VARCHAR(50)  NOT NULL,                   -- 예: 데이트 추천
    slug        VARCHAR(50)  NOT NULL,                   -- 예: date. URL 쿼리(tags=date)에 쓴다
    is_votable  BOOLEAN      NOT NULL DEFAULT FALSE,     -- 사실 정보(시식·체험·반려동물)는 투표 불가
    PRIMARY KEY (id),
    UNIQUE KEY uq_tags_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------------
-- 박람회
-- ---------------------------------------------------------------------------

CREATE TABLE fairs (
    id               BIGINT        NOT NULL AUTO_INCREMENT,
    title            VARCHAR(200)  NOT NULL,
    category_id      INT           NOT NULL,
    venue_id         BIGINT        NOT NULL,
    hall             VARCHAR(100)  NULL,                 -- 예: A홀
    start_date       DATE          NOT NULL,
    end_date         DATE          NOT NULL,
    open_time        TIME          NULL,
    close_time       TIME          NULL,
    hours_note       VARCHAR(255)  NULL,                 -- 예: 마지막 날 16시 마감
    public_access    ENUM('public', 'partial', 'trade_only', 'unknown') NOT NULL DEFAULT 'unknown',
    access_note      VARCHAR(255)  NULL,                 -- 예: 일반인은 13~14일 퍼블릭데이만
    price_onsite     INT           NULL,                 -- 현장 입장료(원). 0 = 무료, NULL = 미확인
    price_prereg     INT           NULL,                 -- 사전등록 입장료(원). 0 = 사전등록 시 무료
    prereg_start_at  DATETIME      NULL,                 -- 사전등록 기간(UTC)
    prereg_end_at    DATETIME      NULL,                 -- 마감 임박 목록·알림 기준
    prereg_url       VARCHAR(500)  NULL,
    official_url     VARCHAR(500)  NULL,
    summary          TEXT          NULL,                 -- 관리자가 직접 쓴 소개 (원문 복제 금지)
    visit_tip        TEXT          NULL,                 -- 주차, 붐비는 시간, 추천 동선
    image_url        VARCHAR(500)  NULL,                 -- 직접 올린 이미지만. 없으면 카테고리 기본 이미지
    status           ENUM('draft', 'published', 'hidden') NOT NULL DEFAULT 'draft',
    source           ENUM('manual', 'crawler', 'api') NOT NULL,
    verified_at      DATETIME      NULL,                 -- 관리자가 공식 정보를 마지막으로 확인한 일시
    created_at       DATETIME      NOT NULL,
    updated_at       DATETIME      NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_fairs_period CHECK (end_date >= start_date),
    CONSTRAINT ck_fairs_price_onsite CHECK (price_onsite IS NULL OR price_onsite >= 0),
    CONSTRAINT ck_fairs_price_prereg CHECK (price_prereg IS NULL OR price_prereg >= 0),
    CONSTRAINT fk_fairs_category FOREIGN KEY (category_id) REFERENCES categories (id),
    CONSTRAINT fk_fairs_venue FOREIGN KEY (venue_id) REFERENCES venues (id),
    KEY ix_fairs_status_start (status, start_date),      -- 공개 박람회 개막순 목록
    KEY ix_fairs_status_end (status, end_date),          -- 진행 중·예정 필터 (end_date >= 오늘)
    KEY ix_fairs_category_start (category_id, start_date),
    KEY ix_fairs_prereg_end (prereg_end_at)              -- 마감 임박 목록, 알림 선별
    -- 11주차: FULLTEXT ft_fairs (title, summary) WITH PARSER ngram 으로 LIKE 검색 대체
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 박람회와 태그 다대다. source 컬럼이 있어 SQLAlchemy 에서는 연관 객체(FairTag)로 다룬다
CREATE TABLE fair_tags (
    fair_id     BIGINT    NOT NULL,
    tag_id      INT       NOT NULL,
    source      ENUM('admin', 'vote') NOT NULL DEFAULT 'admin',
    created_at  DATETIME  NOT NULL,
    PRIMARY KEY (fair_id, tag_id),
    KEY ix_fair_tags_tag (tag_id),                       -- 태그로 박람회 찾기
    CONSTRAINT fk_fair_tags_fair FOREIGN KEY (fair_id) REFERENCES fairs (id),
    CONSTRAINT fk_fair_tags_tag FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 북마크. PK(user_id, fair_id) 덕분에 같은 박람회를 두 번 북마크해도 1건 (PUT 멱등성)
CREATE TABLE bookmarks (
    user_id     BIGINT    NOT NULL,
    fair_id     BIGINT    NOT NULL,
    created_at  DATETIME  NOT NULL,
    PRIMARY KEY (user_id, fair_id),
    KEY ix_bookmarks_fair (fair_id),                     -- 박람회별 북마크 수 (인기순)
    CONSTRAINT fk_bookmarks_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_bookmarks_fair FOREIGN KEY (fair_id) REFERENCES fairs (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------------------
-- 수집 파이프라인 (레퍼런스 8장)
-- ---------------------------------------------------------------------------

CREATE TABLE crawl_sources (
    id                 BIGINT        NOT NULL AUTO_INCREMENT,
    venue_id           BIGINT        NOT NULL,
    parser_key         VARCHAR(50)   NOT NULL,           -- 파서 클래스 등록 키. 예: coex
    list_url           VARCHAR(500)  NOT NULL,
    is_active          BOOLEAN       NOT NULL DEFAULT TRUE,
    policy_checked_at  DATETIME      NULL,               -- robots.txt·이용약관 확인 일시 (15장 수집 정책)
    policy_note        VARCHAR(500)  NULL,
    created_at         DATETIME      NOT NULL,
    updated_at         DATETIME      NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_crawl_sources_parser (parser_key),
    CONSTRAINT fk_crawl_sources_venue FOREIGN KEY (venue_id) REFERENCES venues (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE crawl_runs (
    id             BIGINT    NOT NULL AUTO_INCREMENT,
    source_id      BIGINT    NOT NULL,
    status         ENUM('running', 'succeeded', 'failed') NOT NULL DEFAULT 'running',
    found_count    INT       NOT NULL DEFAULT 0,         -- 발견
    new_count      INT       NOT NULL DEFAULT 0,         -- 신규
    changed_count  INT       NOT NULL DEFAULT 0,         -- 변경
    error_message  TEXT      NULL,
    started_at     DATETIME  NOT NULL,
    finished_at    DATETIME  NULL,
    PRIMARY KEY (id),
    KEY ix_crawl_runs_source_started (source_id, started_at),
    CONSTRAINT fk_crawl_runs_source FOREIGN KEY (source_id) REFERENCES crawl_sources (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 수집 원본과 검수 큐. 관리자가 승인해야 fairs 로 공개된다
CREATE TABLE crawled_items (
    id                 BIGINT        NOT NULL AUTO_INCREMENT,
    source_id          BIGINT        NOT NULL,
    external_id        VARCHAR(255)  NOT NULL,           -- 원본 사이트의 행사 ID 또는 상세 URL
    raw_title          VARCHAR(300)  NOT NULL,
    raw_period         VARCHAR(200)  NULL,               -- 예: 2026.11.19(목) ~ 11.22(일)
    raw_venue          VARCHAR(200)  NULL,               -- 예: 코엑스 A홀
    detail_url         VARCHAR(500)  NULL,
    raw_payload        JSON          NULL,               -- 파싱한 필드 전체
    parsed_start_date  DATE          NULL,               -- 정규화 결과. 실패하면 NULL
    parsed_end_date    DATE          NULL,
    parsed_venue_id    BIGINT        NULL,               -- venue_aliases 매칭 결과
    content_hash       CHAR(64)      NOT NULL,           -- 제목·기간·장소 문자열의 SHA-256
    change_status      ENUM('new', 'changed', 'unchanged') NOT NULL,
    review_status      ENUM('pending', 'approved', 'rejected', 'merged') NOT NULL DEFAULT 'pending',
    fair_id            BIGINT        NULL,               -- 승인·병합 후 연결된 박람회
    first_seen_at      DATETIME      NOT NULL,
    last_seen_at       DATETIME      NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_crawled_items_source_external (source_id, external_id),   -- 중복 판정
    KEY ix_crawled_items_review (review_status),                            -- 검수 큐
    CONSTRAINT fk_crawled_items_source FOREIGN KEY (source_id) REFERENCES crawl_sources (id),
    CONSTRAINT fk_crawled_items_venue FOREIGN KEY (parsed_venue_id) REFERENCES venues (id),
    CONSTRAINT fk_crawled_items_fair FOREIGN KEY (fair_id) REFERENCES fairs (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
