// 목록 API 응답 모양 (backend/app/schemas/fair.py 의 FairListItem)
let seq = 0

export function makeFair(overrides = {}) {
  seq += 1
  return {
    id: seq,
    title: `테스트 박람회 ${seq}`,
    start_date: '2026-11-19',
    end_date: '2026-11-22',
    progress: 'upcoming',
    d_day: 6,
    public_access: 'public',
    price: { onsite: 10000, prereg: 0 },
    prereg_end_at: null,
    image_url: null,
    is_bookmarked: false,
    distance_km: null,
    category: { code: 'food', name: '식음료' },
    venue: { id: 1, name: '코엑스', hall: 'A홀', region: '서울' },
    tags: [],
    ...overrides,
  }
}

export const page = (items, { page = 1, size = 20, total = items.length } = {}) => ({ items, page, size, total })
