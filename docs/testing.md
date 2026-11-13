# 테스트

세 층으로 나눠 테스트합니다. 아래로 갈수록 느리지만 실제 사용과 가깝습니다.

| 층 | 도구 | 어디서 | 개수 | 무엇을 |
| --- | --- | --- | --- | --- |
| 백엔드 | pytest + MySQL 8.4 | `backend/tests/` | 216 | API·서비스·파서·정규화. 테스트마다 트랜잭션 롤백 |
| 프론트 단위·컴포넌트 | Vitest + Testing Library + MSW | `frontend/src/**/*.test.js(x)` | 144 | 포맷 함수, 토큰 재발급, 위치 훅, 화면(홈·목록·캘린더·통계·로그인·가드·비밀번호 재설정·알림 설정·탈퇴·관리자 등록·수집 검수·관람 노트·후기·태그 투표). API 는 MSW 가짜 응답 |
| E2E | Playwright (Chromium) | `frontend/e2e/` | 19 시나리오 × 2 화면 | 실제 API + MySQL + 빌드한 프론트. 데스크톱과 모바일(Pixel 7) 화면 |

CI(GitHub Actions)는 PR 마다 세 층을 모두 돌립니다 (`.github/workflows/ci.yml`).

## 실행

```powershell
# 백엔드 (backend/, 가상환경 켠 상태)
pytest

# 프론트 단위 테스트 (frontend/)
npm test             # 한 번
npm run test:watch   # 파일을 고칠 때마다

# E2E (frontend/). Docker MySQL 이 켜져 있어야 한다
npx playwright install chromium   # 처음 한 번
npm run e2e
npx playwright show-trace test-results\<실패한 테스트>\trace.zip   # 실패 원인 보기
```

## E2E 가 쓰는 서버와 DB

`npm run e2e` 를 실행하면 Playwright 가 서버 두 개를 띄우고, 끝나면 끕니다 (`frontend/playwright.config.js`).

| 서버 | 명령 | 주소 |
| --- | --- | --- |
| API | `python -m app.scripts.e2e_server --port 8001` | http://127.0.0.1:8001 |
| 프론트 | `npm run build` 후 `vite preview` (`/api` 는 8001 로 프록시) | http://localhost:4173 |

`e2e_server` 는 **E2E 전용 DB `fairpick_e2e`** 의 테이블을 모두 지우고, 마이그레이션 → 시드(박람회 30건) → E2E 데이터(관리자 `admin@e2e.example.com`, 검수 대기 수집 항목 4건) 후 API 를 띄웁니다. 그래서 매번 같은 데이터에서 시작하고, 개발 DB(`fairpick`)나 pytest DB(`fairpick_test`)는 건드리지 않습니다. 이름이 `_e2e` 로 끝나지 않는 DB 는 거부합니다.

DB 주소는 `E2E_DATABASE_URL` 이 있으면 그것을, 없으면 `.env` 의 `DATABASE_URL` 에서 DB 이름만 `fairpick_e2e` 로 바꿔 씁니다.

### `fairpick_e2e` DB 만들기 (이미 만든 MySQL 컨테이너)

새 컨테이너는 `docker/mysql-init` 이 자동으로 만들지만, 그 전에 만든 컨테이너에는 한 번 직접 만들어야 합니다.

```powershell
docker exec -it fairpick-db-1 mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS fairpick_e2e CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; GRANT ALL PRIVILEGES ON fairpick_e2e.* TO 'fairpick'@'%';"
```

비밀번호는 `.env` 의 `DB_ROOT_PASSWORD`.

## 시나리오

| 파일 | 시나리오 |
| --- | --- |
| `e2e/browse.spec.js` | 홈 → 목록 → 상세 / 검색 후 새로고침해도 같은 결과 / 카테고리 필터가 URL 에 남고 뒤로 가기로 복귀 / 없는 박람회는 404 |
| `e2e/admin.spec.js` | 관리자: 초안 등록(공개 화면에 안 나옴) → 공개·정보 확인(상세에 무료·태그·확인일) → 숨김(404, 관리자 목록엔 남음) / 수집 항목 승인(카테고리 전엔 비활성, 공개 목록에 나옴, 원본 전시홀 채움)·반려 / 일반 회원은 화면도 API(403)도 막힘 |
| `e2e/engagement.spec.js` | 관람 노트를 공개로 남기면 후기 → 다른 회원 좋아요(새로고침 유지) / 나만 보기는 후기에 안 나옴, 확인 창 거쳐 삭제 / 태그 투표는 로그인 필요, 표 +1 |
| `e2e/account.spec.js` | 가입 → 북마크 → 새로고침해도 유지 → 마이페이지 → 해제 / 비로그인 북마크 → 로그인 → 그 박람회로 복귀, 리프레시 쿠키가 httpOnly / 비로그인 마이페이지 → 로그인 화면 / 마이페이지에서 로그아웃하면 홈 / 탈퇴하면 홈, 앱 안에서 이동해도 공개 화면 정상, 같은 계정 로그인 불가 / 틀린 비밀번호 |
| `e2e/pages.spec.js` | 캘린더: 여러 날 박람회가 기간의 모든 날에, 눌러서 상세, 다음 달 / 통계: 요약 숫자, 실제 차트 막대, 표로 보기(12개월), 카테고리 표 |

계정은 테스트마다 새로 만듭니다(`e2e-<화면>-<시각>@example.com`). 같은 DB 를 쓰므로 순서대로(worker 1개) 돌립니다.
데스크톱·모바일이 같은 DB 를 쓰므로 서로 영향을 주지 않게 작성합니다: 수집 항목은 화면 크기마다 따로 넣어 두고, 박람회 개수·투표 수는 고정값 대신 전후를 비교하고, 내 후기는 고유한 메모로 찾습니다. 공통 동작(가입·로그인·로그아웃·응답 기다리기)은 `e2e/helpers.js`.

## 프론트 단위 테스트 규칙

- API 는 실제로 부르지 않고 MSW 로 응답을 정합니다 (`src/test/server.js`). 정하지 않은 요청이 나가면 테스트가 실패합니다(`onUnhandledRequest: 'error'`).
- 화면은 앱과 같은 공급자(Query·Router·Auth)로 감싸 그립니다 (`src/test/render.jsx`). 로그인 상태는 `loggedInAs()` 로 `/auth/refresh` 응답을 바꿔 만듭니다.
- 지금 주소는 `currentLocation(screen)` 으로 확인합니다 (필터가 URL 에 반영되는지, 로그인 후 어디로 가는지).
- 차트(recharts)는 jsdom 에서 크기를 못 재므로 단위 테스트에서는 숫자로 쓴 문장과 표를 보고(`ResizeObserver` 는 빈 가짜), 실제로 그려지는지는 E2E 로 봅니다.
- 위치 권한은 `vi.mock('../utils/location')` 으로 결과만 정합니다 (`pages/Home.test.jsx`).
- 요소는 역할·이름(`getByRole('button', { name: '북마크' })`)으로 찾습니다. 접근성 이름이 바뀌면 테스트도 깨지므로 스크린 리더 사용자도 같이 지켜집니다.

## E2E 로 찾은 버그

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| 북마크한 박람회 상세에서 새로고침하면 '북마크 1명' 인데 버튼은 안 눌린 상태 | 새로고침 직후 화면이 로그인 복구(`/auth/refresh`)보다 먼저 비로그인으로 데이터를 받고, 복구 뒤 다시 받지 않음 | 복구가 끝나면 진행 중인 요청을 취소하고 쿼리를 무효화해 다시 받음 (`store/AuthContext.jsx`). 무효화만 하면 첫 응답을 기다리는 쿼리는 다시 요청하지 않아 CI 에서만 실패했음 |
| 북마크 → 로그인 화면 → 로그인하면 가끔 원래 박람회가 아니라 홈으로 감 | 로그인 성공으로 user 가 생기는 순간 `GuestOnlyRoute` 가 다시 그려져 홈으로 보내는 것과, 로그인 화면의 `navigate(next)` 가 경쟁 | 가드도 `next` 로 보냄 (`routes/Guards.jsx`) |

| 관리자가 새 박람회를 등록하면 '저장했어요' 가 안 보임 | 등록 후 수정 화면으로 옮기며 폼을 새로 그려(key 변경) 안내 상태가 사라짐 | 이동 상태(`state.saved`)로 넘겨 새 폼이 받아 보여 줌 (`AdminFairEdit.jsx`) |
| 관람 노트를 지워도 고치기 폼이 열린 채 남음 ('삭제' 버튼만 사라진 빈 폼) | 삭제 성공 후 편집 상태를 끄지 않음 | 삭제 성공 시 폼을 닫음 (`FairEngagement.jsx`) |

## 단위 테스트로 찾은 버그

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| 탈퇴하면 홈이 아니라 로그인 화면(`?next=/mypage/settings`)으로 감. 마이페이지에서 로그아웃해도 같음 | React Router 7 은 주소 변경을 transition 으로 처리해, 사용자 상태(null)가 먼저 그려지고 `ProtectedRoute` 가 로그인 화면으로 보냄 | 직접 로그아웃·탈퇴했으면(`signedOut`) 가드도 홈으로 보냄 (`routes/Guards.jsx`). 트러블슈팅 18 |
| 탈퇴 후 앱 안에서 이동하면 공개 목록까지 실패 | 탈퇴할 때 사용자만 지우고 메모리의 액세스 토큰은 남겨, 없는 회원의 토큰으로 요청해 401 | 로그아웃과 같은 `endSession()`(토큰·사용자·캐시 정리)을 씀 (`store/AuthContext.jsx`) |
| 홈 '사전등록 마감 임박' 에 `D-null` | 목록을 받아 둔 사이 마감 시각이 지나면 남은 날이 null | '마감' 으로 표시 (`pages/Home.jsx`) |

모든 버그를 단위 테스트로도 재현해 두었습니다 (고치기 전 코드에서 실패하는 것 확인).
