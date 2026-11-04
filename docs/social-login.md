# 소셜 로그인 키 발급과 설정

코드는 이미 들어 있습니다. 키를 `.env` 에 넣고 서버를 다시 시작하면 로그인·가입 화면에 버튼이 나타납니다.
키가 없으면 버튼이 숨겨지고, 나머지 기능은 그대로 동작합니다.

## 공통: Redirect URI

제공자 콘솔에 등록하는 주소는 `APP_BASE_URL` + 아래 경로이고, **글자 하나까지 같아야** 합니다.

| 환경 | 카카오 | 구글 |
| --- | --- | --- |
| 개발 (`APP_BASE_URL=http://localhost:5173`) | `http://localhost:5173/api/v1/auth/oauth/kakao/callback` | `http://localhost:5173/api/v1/auth/oauth/google/callback` |
| 운영 | `https://도메인/api/v1/auth/oauth/kakao/callback` | `https://도메인/api/v1/auth/oauth/google/callback` |

개발 중에는 Vite 프록시가 `/api` 를 백엔드로 넘기므로 프론트 주소(5173)를 씁니다. 개발용과 운영용을 둘 다 등록해 두면 됩니다.

## 카카오

1. [Kakao Developers](https://developers.kakao.com) → 내 애플리케이션 → 애플리케이션 추가
2. 앱 키의 **REST API 키** → `KAKAO_CLIENT_ID`
3. 카카오 로그인 → 활성화 ON, Redirect URI 등록 (위 표)
4. 카카오 로그인 → 동의항목: **닉네임** 설정. **카카오계정(이메일)** 은 설정할 수 있으면 '선택 동의' 로 켭니다
   - 이메일 항목은 앱 설정(비즈 앱 여부 등)에 따라 켤 수 없을 수 있습니다. 켜지 않아도 로그인은 되고, 그 회원은 이메일 없이 가입됩니다(알림 메일 불가)
   - 서버는 scope 를 따로 요청하지 않고 콘솔의 동의항목을 그대로 씁니다. 설정하지 않은 항목을 요청하면 KOE205 오류가 나기 때문입니다
5. (선택) 보안 → Client Secret 을 켰다면 그 값 → `KAKAO_CLIENT_SECRET`

## 구글

1. [Google Cloud Console](https://console.cloud.google.com) → 프로젝트 만들기
2. API 및 서비스 → OAuth 동의 화면: 사용자 유형 '외부', 앱 이름·지원 이메일 입력, 범위는 `openid`, `email`, `profile`
   - 게시 상태가 '테스트' 인 동안에는 '테스트 사용자' 에 넣은 계정만 로그인할 수 있습니다
3. 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID → 애플리케이션 유형 '웹 애플리케이션'
4. 승인된 리디렉션 URI 에 위 표의 주소 등록
5. 클라이언트 ID → `GOOGLE_CLIENT_ID`, 클라이언트 보안 비밀번호 → `GOOGLE_CLIENT_SECRET`

## 확인

1. `.env` 저장 → 백엔드 다시 시작 (`uvicorn app.main:app --reload` 는 `.env` 변경을 감지하지 못할 수 있음)
2. `GET /api/v1/auth/oauth/providers` → `{"providers": ["kakao", "google"]}`
3. 가입 화면에서 '만 14세 이상' 체크 → 카카오/구글 버튼 → 로그인 → 홈으로 돌아와 로그인 상태
4. 로그아웃 후 로그인 화면의 버튼으로 다시 들어오면 같은 계정

## 동작 규칙 (코드: `backend/app/services/oauth.py`)

| 상황 | 결과 |
| --- | --- |
| 이미 연결된 소셜 계정 | 그 회원으로 로그인 |
| 제공자가 **확인된** 이메일을 주고, 같은 이메일 회원이 있음 | 그 회원에 연결 후 로그인 |
| 제공자의 이메일이 확인되지 않음 | 기존 회원에 연결하지 않음 (남의 이메일로 계정을 가로채는 것 방지) |
| 처음 왔고 가입 화면(만 14세 확인)에서 시작 | 새 회원. 확인된 이메일이 없으면 이메일 없이 |
| 처음 왔는데 로그인 화면에서 시작 | 가입 화면으로 보내 만 14세 확인을 받음 |

소셜로만 가입한 회원은 비밀번호가 없습니다. 이메일이 있으면 '비밀번호 재설정' 으로 비밀번호를 만들어 이메일 로그인도 쓸 수 있습니다.

## 오류 코드 (`/login?oauth_error=…`)

| 코드 | 뜻 |
| --- | --- |
| `OAUTH_NOT_CONFIGURED` | 키가 설정되지 않음 |
| `OAUTH_STATE_MISMATCH` | state 쿠키가 없거나 다름 (10분 초과, 다른 브라우저, 위조) |
| `OAUTH_CANCELLED` | 제공자 화면에서 취소 |
| `OAUTH_PROVIDER_ERROR` | 토큰·사용자 정보 요청 실패. 서버 로그에 응답 내용이 남음 (Redirect URI 불일치가 가장 흔함) |
| `OAUTH_SIGNUP_REQUIRED` | 처음 온 사람이 로그인 화면에서 시작함 → 가입 화면으로 |
