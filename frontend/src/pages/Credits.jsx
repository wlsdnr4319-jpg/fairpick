import { pexelsPage, STOCK_PHOTOS, stockSrc } from '../utils/stockPhotos'

// 사진 출처. 표지 예시 사진은 Pexels 라이선스라 출처 표시 의무는 없지만, 누구 사진인지 모두 밝혀 둔다.
const LABELS = {
  coffee: '커피',
  teapot: '차',
  drinks: '주류',
  noodles: '면 요리',
  dessert: '디저트·베이커리',
  plate: '식음료',
  cat: '고양이',
  dog: '강아지',
  paw: '반려동물',
  dice: '보드게임',
  controller: '게임',
  cards: '카드 게임',
  palette: '미술',
  frame: '문화·예술',
  pencil: '일러스트·만화',
  plush: '인형·토이',
  sofa: '리빙·인테리어',
  vase: '공예',
  christmas: '크리스마스',
  rings: '웨딩',
  balloons: '베이비·키즈',
  tent: '캠핑',
  suitcase: '여행',
  gift: '선물',
  coins: '재테크',
  calendar: '도서·문구',
  flower: '꽃·가든',
  bag: '마켓',
  ticket: '축제·레저',
}

export default function Credits() {
  return (
    <article className="space-y-6">
      <header className="max-w-2xl space-y-2 text-sm leading-relaxed text-gray-700">
        <h1 className="text-2xl font-bold text-gray-900">사진 출처</h1>
        <p>
          박람회 카드와 상세 화면의 <strong>예시 사진</strong>은 그 박람회에서 찍은 사진이 아니라, 주제가 같은 무료 사진입니다.
          모두{' '}
          <a href="https://www.pexels.com/license/" target="_blank" rel="noreferrer" className="text-indigo-700 underline">
            Pexels 라이선스
          </a>
          (무료 사용·수정 가능)를 따릅니다.
        </p>
        <p>주최 측이 사용을 허락했거나 직접 찍은 사진이 있으면 그 사진을 먼저 씁니다. 공식 포스터는 저작권이 있어 쓰지 않습니다.</p>
      </header>

      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(STOCK_PHOTOS).map(([key, photo]) => (
          <li key={key} className="overflow-hidden rounded-xl border">
            <img src={stockSrc(key, 640)} alt="" width={320} height={160} loading="lazy" decoding="async" className="aspect-[2/1] w-full object-cover" />
            <div className="min-w-0 p-3 text-sm">
              <p className="font-semibold text-gray-900">{LABELS[key.replace(/2$/, '')] ?? key}</p>
              <p className="truncate text-gray-600">
                사진:{' '}
                <a href={pexelsPage(photo)} target="_blank" rel="noreferrer" className="text-indigo-700 underline">
                  {photo.author} / Pexels
                </a>
              </p>
            </div>
          </li>
        ))}
      </ul>
    </article>
  )
}
