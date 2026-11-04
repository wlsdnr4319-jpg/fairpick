import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../api/health'

// 홈 큐레이션(이번 주말, 사전등록 마감 임박, 카테고리 바로가기)은 3주차에 만든다.
// 지금은 서비스 소개와 API 연결 상태만 보여준다.
export default function Home() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  })

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">이번 주말, 어떤 박람회 갈까요?</h1>
      <p className="text-gray-600">
        식음료·문화·이색 박람회를 한곳에 모으고, 일반인 관람 조건과 사전등록 마감까지 알려드려요.
      </p>

      <p className="text-sm" aria-live="polite">
        {isPending && <span className="text-gray-400">API 연결 확인 중…</span>}
        {isError && <span className="text-red-600">API에 연결할 수 없어요. 백엔드가 켜져 있는지 확인하세요.</span>}
        {data?.status === 'ok' && <span className="text-green-600">API 연결됨</span>}
      </p>
    </section>
  )
}
