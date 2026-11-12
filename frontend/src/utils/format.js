// 화면 표시용 포맷만 클라이언트에서 만든다. 진행 상태와 D-day 는 서버가 한국 시간으로 계산해 준다 (레퍼런스 11장).
const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

function parseDate(ymd) {
  const [y, m, d] = ymd.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function md(ymd) {
  const d = parseDate(ymd)
  return `${d.getMonth() + 1}.${d.getDate()}(${WEEKDAYS[d.getDay()]})`
}

// 예: 11.19(목) ~ 11.22(일). 해가 다르면 연도를 붙인다
export function formatPeriod(start, end) {
  if (start === end) return md(start)
  const sy = start.slice(0, 4)
  const ey = end.slice(0, 4)
  return sy === ey ? `${md(start)} ~ ${md(end)}` : `${sy}.${md(start)} ~ ${ey}.${md(end)}`
}

// 서버가 +09:00 로 준 일시 → "11.16(월) 23:59"
export function formatDateTime(iso) {
  if (!iso) return ''
  const [date, time] = iso.split('T')
  return `${md(date)} ${time.slice(0, 5)}`
}

export function formatPrice(value) {
  if (value == null) return '확인 중'
  if (value === 0) return '무료'
  return `${value.toLocaleString('ko-KR')}원`
}

export function statusLabel(progress, dDay) {
  if (progress === 'ongoing') return '진행 중'
  if (progress === 'ended') return '종료'
  return dDay === 0 ? 'D-day' : `D-${dDay}`
}

// 사전등록 마감까지 남은 일수 (마감 일시 기준, 한국 시간)
export function deadlineDDay(iso) {
  if (!iso) return null
  const diff = new Date(iso).getTime() - Date.now()
  if (diff < 0) return null
  return Math.floor(diff / 86_400_000)
}

export const PUBLIC_ACCESS_LABEL = {
  public: '일반인 관람 가능',
  partial: '일부 날짜만 일반인 관람',
  trade_only: '업계 종사자 전용',
  unknown: '관람 조건 확인 중',
}

// 거리(km). 위치를 약 1km 단위로 줄여 보내므로 소수점까지 보여 주지 않는다
export function formatDistance(km) {
  if (km == null) return ''
  return km < 1 ? '1km 이내' : `약 ${Math.round(km).toLocaleString('ko-KR')}km`
}
