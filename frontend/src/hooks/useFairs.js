import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { fetchCategories, fetchFair, fetchFairs, fetchTags, fetchVenues, setBookmark } from '../api/fairs'

// 목록의 필터·정렬·페이지는 URL 쿼리스트링을 기준으로 삼는다 (레퍼런스 11장)
export function useFairsFromUrl() {
  const [searchParams] = useSearchParams()
  const params = Object.fromEntries(searchParams)
  // 위치가 빠진 거리순 주소(일부만 복사한 링크 등)는 오류 대신 기본 정렬로 보여 준다
  if (!(params.lat && params.lng)) {
    if (params.sort === 'distance') delete params.sort
    delete params.radius_km
  }
  return useQuery({
    queryKey: ['fairs', params],
    queryFn: () => fetchFairs(params),
    placeholderData: keepPreviousData, // 페이지를 넘길 때 이전 목록 유지
  })
}

export function useFairs(params) {
  return useQuery({ queryKey: ['fairs', params], queryFn: () => fetchFairs(params) })
}

export function useFair(fairId) {
  return useQuery({ queryKey: ['fair', String(fairId)], queryFn: () => fetchFair(fairId) })
}

// 필터용 참조 데이터는 자주 바뀌지 않아 오래 캐시한다
const REF = { staleTime: 10 * 60_000 }
export const useCategories = () => useQuery({ queryKey: ['categories'], queryFn: fetchCategories, ...REF })
export const useTags = () => useQuery({ queryKey: ['tags'], queryFn: fetchTags, ...REF })
export const useVenues = () => useQuery({ queryKey: ['venues'], queryFn: fetchVenues, ...REF })

// 북마크는 낙관적 업데이트: 화면을 먼저 바꾸고, 요청이 실패하면 되돌린다 (레퍼런스 11장)
export function useBookmark(fairId) {
  const qc = useQueryClient()

  const patch = (on) => (old) => {
    if (!old) return old
    if (old.items) {
      return { ...old, items: old.items.map((i) => (i.id === fairId ? { ...i, is_bookmarked: on } : i)) }
    }
    if (old.id === fairId) {
      return { ...old, is_bookmarked: on, bookmark_count: Math.max(0, old.bookmark_count + (on ? 1 : -1)) }
    }
    return old
  }

  return useMutation({
    mutationFn: (on) => setBookmark(fairId, on),
    onMutate: async (on) => {
      await qc.cancelQueries({ queryKey: ['fairs'] })
      await qc.cancelQueries({ queryKey: ['fair', String(fairId)] })
      const snapshot = [...qc.getQueriesData({ queryKey: ['fairs'] }), ...qc.getQueriesData({ queryKey: ['fair'] })]
      qc.setQueriesData({ queryKey: ['fairs'] }, patch(on))
      qc.setQueriesData({ queryKey: ['fair', String(fairId)] }, patch(on))
      return { snapshot }
    },
    onError: (_err, _on, ctx) => ctx?.snapshot.forEach(([key, data]) => qc.setQueryData(key, data)),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['fair', String(fairId)] })
      qc.invalidateQueries({ queryKey: ['bookmarks'] })
    },
  })
}
