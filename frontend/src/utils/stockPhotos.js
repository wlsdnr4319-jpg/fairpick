// 표지 예시 사진 (Pexels 라이선스: 무료, 수정 가능, 출처 표시 의무 없음 — 그래도 /credits 에 모두 적는다).
// 그 박람회의 사진이 아니라 주제가 같은 사진이다. 키는 utils/cover.js 의 그림(motif) 이름과 같다.
// 파일은 public/covers/{키}-640.webp(카드), {키}-1280.webp(상세·고해상도). 2:1 로 잘라 WebP 로 줄여 두었다.
export const STOCK_PHOTOS = {
  coffee: { id: 459489, slug: 'cup-of-coffee-on-saucer', author: 'pixabay' },
  teapot: { id: 36462130, slug: 'vintage-blue-and-white-teapot-with-cups-on-table', author: 'soc-nang-d-ng-2150345854' },
  drinks: { id: 7283342, slug: 'clear-wine-glasses-with-red-wine', author: 'polina-kovaleva' },
  noodles: { id: 16671603, slug: 'fingers-holding-food-in-chopsticks', author: 'luis-c-tavera-2750113' },
  dessert: { id: 27497012, slug: 'a-tray-of-cakes-with-strawberries-and-blueberries', author: 'teysa-tugadi-1282097472' },
  plate: { id: 7239432, slug: 'food-dishes-on-the-table', author: 'furkanfdemir' },
  cat: { id: 6145891, slug: 'a-close-up-shot-of-a-cat', author: 'samuelsweet' },
  dog: { id: 35445396, slug: 'adorable-brown-and-white-puppy-outdoors', author: 'musstashy' },
  paw: { id: 16395150, slug: 'dog-and-cat-sitting-together', author: 'helen1' },
  dice: { id: 8111328, slug: 'hands-playing-board-games', author: 'pavel-danilyuk' },
  controller: { id: 7887636, slug: 'a-pair-of-camouflage-game-controller-on-black-surface', author: 'mikhail-nilov' },
  cards: { id: 6838595, slug: 'a-hand-putting-the-playing-cards-on-the-wooden-table', author: 'kampus' },
  palette: { id: 34149478, slug: 'vibrant-paint-palettes-on-artist-s-table', author: 'gunnar-hoffmann-2154527493' },
  frame: { id: 40025998, slug: 'art-gallery-hallway-with-paintings-displayed', author: 'hson' },
  pencil: { id: 4238483, slug: 'person-drawing-on-a-sketchbook', author: 'ivan-s' },
  plush: { id: 20692469, slug: 'teddy-bears-on-yellow-blanket', author: 'nano-erdozain-120534369' },
  sofa: { id: 7546648, slug: 'interior-design-of-room', author: 'artbovich' },
  vase: { id: 29286722, slug: 'rustic-pottery-cups-and-bowls-on-wooden-shelves', author: 'novirina-ru' },
  christmas: { id: 29820836, slug: 'festive-display-of-christmas-snow-globes-and-ornaments', author: 'nuraynuna' },
  rings: { id: 265856, slug: 'selective-focus-photography-of-silver-colored-engagement-ring-set-with-pink-bow-accent-on-throw-pillow', author: 'pixabay' },
  balloons: { id: 7499406, slug: 'baby-sitting-on-a-colorful-puzzle-mat', author: 'meruyert-gonullu' },
  tent: { id: 4268094, slug: 'bright-camping-tents-on-top-of-hill-on-overcast-weather', author: 'quang-nguyen-vinh-222549' },
  suitcase: { id: 7009459, slug: 'a-desk-globe-on-a-black-luggage', author: 'tima-miroshnichenko' },
  gift: { id: 1303087, slug: 'white-and-red-gift-boxes', author: 'george-dolgikh-551816' },
  coins: { id: 6534323, slug: 'a-wooden-money-box-on-assorted-coins', author: 'debraj' },
  calendar: { id: 5124869, slug: 'a-planner-and-textbooks-lying-on-brown-background', author: 'cottonbro' },
  flower: { id: 31497181, slug: 'colorful-spring-flower-bouquets-in-outdoor-market', author: 'ilayda0700' },
  bag: { id: 37813600, slug: 'colorful-outdoor-market-stall-with-clothing-display', author: 'neslihan-ercan-58134101' },
  ticket: { id: 36513643, slug: 'vibrant-night-festival-with-illuminated-tents', author: 'beyzaa-279977530' },
  // 카테고리 기본 사진은 여러 박람회가 같이 쓰므로 두 번째 사진을 두고 번갈아 쓴다 (stockKey)
  plate2: { id: 29732925, slug: 'appetizing-snack-platter-with-dips-and-delights', author: 'vince' },
  frame2: { id: 15138863, slug: 'photographies-on-display-in-station', author: 'bertellifotografia' },
  bag2: { id: 33512943, slug: 'charming-flea-market-with-vintage-finds', author: 'kemalcanfilm-33512943' },
  ticket2: { id: 16046217, slug: 'shining-lanterns-at-night', author: 'mehrajul-karim-114876029' },
  paw2: { id: 20816519, slug: 'dog-lying-down-and-cat-sitting', author: 'wanderkash' },
  balloons2: { id: 11116578, slug: 'toys-in-a-baby-crib', author: 'wolfart' },
  controller2: { id: 34592708, slug: 'illuminated-gaming-controllers-on-dark-surface', author: 'ucantereyagi' },
}

export const stockPhoto = (motif) => STOCK_PHOTOS[motif] ?? null

// 그림 이름 → 사진 키. 두 번째 사진이 있으면 박람회 id 로 둘 중 하나를 고른다 (같은 박람회는 늘 같은 사진)
export function stockKey(motif, fairId) {
  const second = `${motif}2`
  if (!STOCK_PHOTOS[motif]) return null
  return STOCK_PHOTOS[second] && Number(fairId) % 2 === 1 ? second : motif
}

export const stockSrc = (motif, width) => `/covers/${motif}-${width}.webp`

export const pexelsPage = ({ id, slug }) => `https://www.pexels.com/photo/${slug}-${id}/`
