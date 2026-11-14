// 박람회 표지 일러스트 고르기 (FairCover 가 그린다).
// 공식 포스터는 저작권이 있어 저장·복제하지 않는다. 대신 제목 키워드와 카테고리로 우리가 그린 그림을 고른다.

// 카테고리별 색: 배경 그라데이션(from → to), 선(ink), 강조색(accent)
export const CATEGORY_PALETTE = {
  food: { from: '#fde68a', to: '#fdba74', ink: '#7c2d12', accent: '#fb923c' },
  culture: { from: '#fbcfe8', to: '#fda4af', ink: '#881337', accent: '#f472b6' },
  lifestyle: { from: '#99f6e4', to: '#6ee7b7', ink: '#134e4a', accent: '#2dd4bf' },
  leisure: { from: '#bae6fd', to: '#93c5fd', ink: '#1e3a8a', accent: '#60a5fa' },
  pet: { from: '#fef08a', to: '#bef264', ink: '#365314', accent: '#84cc16' },
  family: { from: '#ddd6fe', to: '#d8b4fe', ink: '#4c1d95', accent: '#a78bfa' },
  tech: { from: '#e0e7ff', to: '#a5b4fc', ink: '#1e1b4b', accent: '#818cf8' },
}
const DEFAULT_PALETTE = { from: '#e5e7eb', to: '#d1d5db', ink: '#1f2937', accent: '#9ca3af' }

export const paletteFor = (categoryCode) => CATEGORY_PALETTE[categoryCode] ?? DEFAULT_PALETTE

// 위에서부터 먼저 맞는 그림을 쓴다 (순서 = 우선순위).
// 예: '크리스마스 서울펫쇼' 는 동물이 먼저라 발바닥, '홈앤리빙 더아트페스타' 는 가구가 먼저라 소파,
// '아웃도어캠핑&레포츠페스티벌' 은 캠핑이 아트보다 먼저라 텐트.
const RULES = [
  ['cat', ['캣', '고양이', 'cat']],
  ['dog', ['도그', '강아지', '애견', 'dog']],
  ['paw', ['펫', '반려', 'pet']],
  ['christmas', ['크리스마스', '성탄', 'christmas']],
  ['rings', ['웨딩', '결혼', '혼수', 'wedding']],
  ['balloons', ['베이비', '유아', '육아', '출산', '키즈', 'baby', 'kids']],
  ['dice', ['보드게임', 'boardgame']],
  ['cards', ['카드', 'tcg']],
  ['controller', ['게임', '플레이엑스포', 'game']],
  ['coffee', ['커피', '카페', 'coffee', 'cafe']],
  ['teapot', ['티&', '티페어', '차문화', '세계차', '茶', '다도', 'tea']],
  ['drinks', ['위스키', '와인', '주류', '맥주', '사케', '전통주', '칵테일', '하이볼', '캐스크', 'wine', 'beer', 'whisk']],
  ['noodles', ['라면', '국수', '누들', '면페스타']],
  ['dessert', ['디저트', '베이커리', '빵', '케이크', '쿠키', '초콜릿', 'dessert', 'bakery']],
  ['pencil', ['일러스트', '코믹', '만화', '웹툰', '동인', '온리전', '캐릭터', 'illust', 'comic']],
  ['plush', ['솜', '인형', '토이', '피규어', 'doll', 'toy']],
  ['sofa', ['가구', '인테리어', '리빙', '하우징', '건축', '홈', 'furni', 'living']],
  ['vase', ['공예', '크래프트', '핸드메이드', '도자', 'craft']],
  ['tent', ['캠핑', '캠페어', '차박', '카라반', '아웃도어', 'camp']],
  ['palette', ['아트', '미술', '갤러리', '그림', 'art']],
  ['suitcase', ['트래블', '여행', '관광', 'travel']],
  ['gift', ['선물', '명절', 'gift']],
  ['coins', ['재테크', '금융', '부동산', '투자', '머니', 'money']],
  ['calendar', ['새해', '캘린더', '다이어리', '문구', '도서', '북페어']],
  ['flower', ['꽃', '플라워', '가든', '정원', 'flower', 'garden']],
  ['bag', ['마켓', '장터', '쇼핑', '밀리언쇼', 'market']],
]

// 키워드가 없을 때 카테고리 기본 그림
const CATEGORY_MOTIF = {
  food: 'plate',
  culture: 'frame',
  lifestyle: 'bag',
  leisure: 'ticket',
  pet: 'paw',
  family: 'balloons',
  tech: 'controller',
}

const ASCII_WORD = /^[a-z]+$/

// 한글 키워드는 띄어쓰기를 뺀 제목에 들어 있으면 맞는다 ('서울 카페 쇼' = '서울카페쇼').
// 영어 키워드는 낱말 시작에서만 맞는다: 'art' 가 'PART 2', 'pet' 이 'carpet' 에 걸리지 않게.
function matches(lower, compact, word) {
  if (ASCII_WORD.test(word)) return new RegExp(`(^|[^a-z])${word}`).test(lower)
  return compact.includes(word)
}

export function pickMotif(title = '', categoryCode) {
  const lower = title.toLowerCase()
  const compact = lower.replace(/\s+/g, '')
  for (const [motif, words] of RULES) {
    if (words.some((w) => matches(lower, compact, w))) return motif
  }
  return CATEGORY_MOTIF[categoryCode] ?? 'ticket'
}

// 박람회 id 로 정해지는 난수 (mulberry32). 같은 박람회는 언제나 같은 장식이 나온다.
export function seededRandom(seed) {
  let a = (Number(seed) || 0) + 0x6d2b79f5
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
