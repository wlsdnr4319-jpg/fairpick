import { useQuery } from '@tanstack/react-query'
import { fetchOAuthProviders } from '../api/auth'

// 제공자 이름·색은 각 사 로그인 버튼 가이드의 기본 배색을 따른다 (로고 이미지는 쓰지 않는다)
const PROVIDERS = {
  kakao: { label: '카카오로 계속하기', className: 'bg-[#FEE500] text-black/85' },
  google: { label: 'Google로 계속하기', className: 'border border-gray-300 bg-white text-gray-800' },
}

export const NEXT_KEY = 'oauth_next' // 소셜 로그인에서 돌아온 뒤 갈 페이지

// 소셜 로그인 버튼. 서버로 이동(전체 페이지 이동)하고, 제공자 로그인 후 /oauth/callback 으로 돌아온다.
// signup: 가입 화면에서 누른 경우 (만 14세 이상 확인을 마쳤다는 뜻). disabled 면 누를 수 없다
export default function SocialButtons({ signup = false, disabled = false, next = '/' }) {
  const { data: providers = [] } = useQuery({
    queryKey: ['oauth-providers'],
    queryFn: fetchOAuthProviders,
    staleTime: Infinity,
  })
  const available = providers.filter((p) => PROVIDERS[p])
  if (available.length === 0) return null

  const go = (provider) => {
    try {
      sessionStorage.setItem(NEXT_KEY, next)
    } catch {
      // 저장소를 못 쓰면 홈으로 돌아온다
    }
    window.location.href = `/api/v1/auth/oauth/${provider}/start?signup=${signup}`
  }

  return (
    <div className="space-y-2">
      <p className="flex items-center gap-3 text-xs text-gray-400 before:h-px before:flex-1 before:bg-gray-200 after:h-px after:flex-1 after:bg-gray-200">
        또는
      </p>
      {available.map((p) => (
        <button
          key={p}
          type="button"
          disabled={disabled}
          onClick={() => go(p)}
          className={`min-h-11 w-full rounded-lg text-sm font-medium disabled:opacity-50 ${PROVIDERS[p].className}`}
        >
          {PROVIDERS[p].label}
        </button>
      ))}
    </div>
  )
}

// 서버가 /login?oauth_error=코드 로 돌려보낼 때 보여줄 문구
const OAUTH_ERRORS = {
  OAUTH_NOT_CONFIGURED: '지금은 이 방법으로 로그인할 수 없어요',
  OAUTH_STATE_MISMATCH: '로그인 요청이 만료됐어요. 다시 시도해 주세요',
  OAUTH_CANCELLED: '소셜 로그인을 취소했어요',
  OAUTH_PROVIDER_ERROR: '소셜 로그인 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요',
  OAUTH_SIGNUP_REQUIRED: '처음 오셨네요! 만 14세 이상인지 확인한 뒤 아래 버튼으로 가입해 주세요',
}

// eslint-disable-next-line react-refresh/only-export-components
export function oauthErrorMessage(code) {
  if (!code) return ''
  return OAUTH_ERRORS[code] ?? '소셜 로그인에 실패했어요. 다시 시도해 주세요'
}
