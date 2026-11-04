# 면접 준비 노트

설계 레퍼런스 17장의 예상 질문에, 실제 구현에서 확인한 근거를 붙였습니다.

| 질문 | 답변 포인트 | 코드 |
| --- | --- | --- |
| 진행 상태를 왜 DB 에 저장하지 않았나요? | 날짜로 계산되는 값을 저장하면 매일 갱신해야 하고 어긋난다. '오늘'은 앱에서 KST 로 계산해 넘긴다 | `app/core/timeutil.py` |
| 수집한 데이터를 왜 바로 공개하지 않나요? | 일반인 관람 여부는 자동 판별이 어렵고 틀린 정보는 신뢰를 잃는다. 검수 큐에서 사람이 채운 뒤 승인 | `app/services/crawl.py`, `routers/admin_crawl.py` |
| 사이트 구조가 바뀌면? | 수집 실패를 `crawl_runs` 에 남기고 2회 연속이면 관리자 메일. 수동 입력으로 서비스 유지, fixture 를 새로 저장해 파서 수정 | `alert_if_repeated_failures`, `tests/fixtures/html` |
| 알림이 중복으로 안 간다는 걸 어떻게 보장하나요? | UNIQUE 제약 + `INSERT IGNORE`. 작업이 두 번 돌아도 1건. 테스트로 확인 | `services/notifications.py`, `tests/test_notifications.py` |
| 인덱스는 어떤 기준으로 만들었나요? | 실제 WHERE·ORDER BY 조합: `(status, start_date)` 개막순, `(status, end_date)` 진행 중 필터, `prereg_end_at` 마감 임박, ngram FULLTEXT 검색 | `models/fair.py` |
| 토큰은 어디에 저장하나요? | 액세스 토큰은 메모리, 리프레시 토큰은 httpOnly·SameSite=Lax 쿠키(Path 제한), DB 에는 SHA-256 해시. 회전하고 재사용 시 전체 폐기 | `services/auth.py`, `frontend/src/api/client.js` |
| 비슷한 앱이 있는데 차별점은요? | 일정 모음이 아니라 일반인 관점 큐레이션: 관람 가능 여부(전체/일부/업계 전용), 관람 팁, 후기, 태그 투표 | |
| 동기 엔드포인트를 쓴 이유는? | `async def` 안에서 동기 DB 드라이버를 호출하면 이벤트 루프가 막혀 다른 요청까지 느려진다. MVP 는 `def` + 스레드풀 | `app/db/session.py` |
| 비밀번호 재설정에서 신경 쓴 점은? | 가입 여부와 관계없이 같은 응답(이메일 존재 여부 노출 방지), 30분·1회용·해시 저장, 성공 시 모든 세션 폐기 | `routers/auth.py` |
| 서비스직 경험이 개발에 어떻게 도움이 됐나요? | 현장에서 손님이 실제로 묻던 것(주차, 붐비는 시간, 동선)을 '관람 팁' 필드로 설계 | `fairs.visit_tip` |
