# ERD

1단계(MVP) 테이블 12개의 관계도다. 컬럼 정의와 인덱스는 [schema.sql](schema.sql)에 있다.

```mermaid
erDiagram
    users ||--o{ refresh_tokens : "has"
    users ||--o{ bookmarks : "makes"
    fairs ||--o{ bookmarks : "receives"
    categories ||--o{ fairs : "groups"
    venues ||--o{ fairs : "hosts"
    venues ||--o{ venue_aliases : "known as"
    fairs ||--o{ fair_tags : "has"
    tags ||--o{ fair_tags : "labels"
    venues ||--o{ crawl_sources : "crawled from"
    crawl_sources ||--o{ crawl_runs : "logs"
    crawl_sources ||--o{ crawled_items : "collects"
    venues |o--o{ crawled_items : "matched to"
    fairs |o--o{ crawled_items : "linked to"

    users {
        bigint id PK
        varchar email UK
        varchar password_hash
        varchar nickname
        enum role "user | admin"
    }
    refresh_tokens {
        bigint id PK
        bigint user_id FK
        char token_hash UK "SHA-256"
        datetime expires_at
        datetime revoked_at "NULL"
        bigint replaced_by_id FK "NULL, 회전으로 대신 발급한 토큰"
    }
    venues {
        bigint id PK
        varchar name UK
        varchar region "시·도"
        varchar address
        decimal latitude
        decimal longitude
        varchar parking_note
    }
    venue_aliases {
        bigint id PK
        bigint venue_id FK
        varchar alias UK
    }
    categories {
        int id PK
        varchar code UK
        varchar name
        int sort_order
    }
    fairs {
        bigint id PK
        varchar title
        int category_id FK
        bigint venue_id FK
        date start_date
        date end_date
        enum public_access "public | partial | trade_only | unknown"
        int price_onsite "0 = 무료, NULL = 미확인"
        int price_prereg
        datetime prereg_end_at
        enum status "draft | published | hidden"
        enum source "manual | crawler | api"
        datetime verified_at
    }
    tags {
        int id PK
        varchar slug UK
        varchar name
        boolean is_votable
    }
    fair_tags {
        bigint fair_id PK, FK
        int tag_id PK, FK
        enum source "admin | vote"
    }
    bookmarks {
        bigint user_id PK, FK
        bigint fair_id PK, FK
        datetime created_at
    }
    crawl_sources {
        bigint id PK
        bigint venue_id FK
        varchar parser_key UK
        varchar list_url
        boolean is_active
        datetime policy_checked_at
    }
    crawl_runs {
        bigint id PK
        bigint source_id FK
        enum status "running | succeeded | failed"
        int found_count
        int new_count
        int changed_count
    }
    crawled_items {
        bigint id PK
        bigint source_id FK
        varchar external_id "UK(source_id, external_id)"
        varchar raw_title
        date parsed_start_date
        bigint parsed_venue_id FK
        char content_hash
        enum change_status "new | changed | unchanged"
        enum review_status "pending | approved | rejected | merged"
        bigint fair_id FK "NULL"
    }
```

## 설계 포인트

- **진행 상태와 D-day는 컬럼이 없다.** 조회할 때 `start_date`, `end_date`와 오늘(KST)로 계산한다. 저장하면 매일 갱신해야 하고 값이 어긋날 수 있다.
- **`price_onsite = NULL`과 `0`은 다르다.** NULL은 아직 모름, 0은 무료다.
- **박람회는 지우지 않는다.** `status = 'hidden'`으로 숨겨 북마크 기록을 보존한다.
- **수집 결과는 바로 공개되지 않는다.** `crawled_items`(검수 큐)에 쌓인 뒤 관리자가 승인해야 `fairs`가 된다.
- **2단계 이후 테이블**(visits, visit_likes, tag_votes, notification_settings, notifications, fair_change_logs, password_reset_tokens, login_attempts, social_accounts)은 해당 주차에 Alembic 마이그레이션으로 추가한다.
