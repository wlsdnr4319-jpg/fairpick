import { paletteFor, pickMotif, seededRandom } from '../utils/cover'

// 박람회 표지. 관리자가 넣은 이미지(image_url)가 있으면 그걸, 없으면 제목·카테고리로 고른 일러스트를 그린다.
// 그림은 100×100 좌표로 그리고, 표지 크기에 맞춰 옮긴다. 장식(원·점)은 박람회 id 로 조금씩 달라진다.

const SIZES = {
  card: { w: 320, h: 144, motif: 104, x: 0.64 },
  hero: { w: 640, h: 220, motif: 168, x: 0.72 },
}

const RED = '#ef4444'
const GOLD = '#facc15'

// 그림마다 fill 기본값은 흰색, 선은 카테고리 ink 색 (아래 <g> 에서 지정)
const MOTIFS = {
  coffee: ({ accent }) => (
    <>
      <path d="M16 88h66" fill="none" />
      <path d="M24 42h46v20a20 20 0 0 1-20 20h-6a20 20 0 0 1-20-20z" />
      <path d="M70 48h5a9 9 0 0 1 0 18h-6" fill="none" />
      <path d="M36 32c-4-5 4-9 0-15M47 32c-4-5 4-9 0-15M58 32c-4-5 4-9 0-15" fill="none" />
      <path d="M47 70c-6-4-8-8-5-11 2-2 4-1 5 1 1-2 3-3 5-1 3 3 1 7-5 11z" fill={accent} stroke="none" />
    </>
  ),
  teapot: ({ accent }) => (
    <>
      <path d="M12 86h76" fill="none" />
      <path d="M25 58C14 56 10 46 8 40c8 2 12 8 17 10" />
      <path d="M76 56c12-2 14 16 0 18" fill="none" />
      <path d="M24 50h52c2 20-8 32-26 32S22 70 24 50z" />
      <path d="M34 50c0-10 32-10 32 0" />
      <circle cx="50" cy="38" r="4" fill={accent} />
      <path d="M30 63h40" fill="none" stroke={accent} />
    </>
  ),
  drinks: ({ accent }) => (
    <>
      <path d="M68 12h10v14c8 4 10 10 10 16v44H58V42c0-6 2-12 10-16z" />
      <rect x="62" y="50" width="22" height="18" rx="3" fill={accent} />
      <path d="M12 40h42l-4 46H16z" />
      <path d="M14.6 62h36.8l-2 24H16.6z" fill={accent} stroke="none" opacity="0.75" />
      <rect x="22" y="54" width="11" height="11" rx="2" transform="rotate(-15 27 59)" />
      <path d="M12 40h42l-4 46H16z" fill="none" />
    </>
  ),
  noodles: ({ accent }) => (
    <>
      <path d="M60 8L42 50M74 10L52 50" fill="none" />
      <path d="M26 50c0-10 6-10 6 0s6 10 6 0 6-10 6 0 6 10 6 0 6-10 6 0 6 10 6 0 6-10 6 0" fill="none" />
      <circle cx="64" cy="46" r="7" />
      <circle cx="64" cy="46" r="3" fill={GOLD} stroke="none" />
      <path d="M12 50h76a38 32 0 0 1-76 0z" />
      <path d="M19 62h62" fill="none" stroke={accent} />
      <path d="M38 80h24l-2 8H40z" />
    </>
  ),
  dessert: ({ accent }) => (
    <>
      <path d="M28 56h44l-6 30H34z" fill={accent} />
      <path d="M40 58l2 28M50 58v28M60 58l-2 28" fill="none" />
      <path d="M24 57c-5-12 7-19 13-14 1-12 25-12 26 0 6-5 18 2 13 14z" />
      <path d="M50 26c0-6 4-9 8-10" fill="none" />
      <circle cx="50" cy="31" r="6" fill={RED} />
    </>
  ),
  plate: ({ accent }) => (
    <>
      <circle cx="50" cy="52" r="27" />
      <circle cx="50" cy="52" r="17" fill="none" stroke={accent} />
      <path d="M10 24v16a5 5 0 0 0 10 0V24M15 24v60" fill="none" />
      <path d="M88 24c-7 6-7 20 0 26v34" fill="none" />
    </>
  ),
  cat: ({ ink, accent }) => (
    <>
      <path d="M22 44L24 14l20 16h12l20-16 2 30c4 24-12 38-28 38S18 68 22 44z" />
      <path d="M29 24l1 11 8-6zM71 24l-1 11-8-6z" fill={accent} stroke="none" />
      <ellipse cx="38" cy="52" rx="3.5" ry="5" fill={ink} stroke="none" />
      <ellipse cx="62" cy="52" rx="3.5" ry="5" fill={ink} stroke="none" />
      <path d="M46 61h8l-4 4z" fill={accent} />
      <path d="M50 65c-2 4-6 4-8 2M50 65c2 4 6 4 8 2" fill="none" />
      <path d="M30 61H12M30 67l-16 4M70 61h18M70 67l16 4" fill="none" />
    </>
  ),
  dog: ({ ink, accent }) => (
    <>
      <path d="M26 30c-14 0-18 26-8 36 6-2 10-12 12-20z" fill={accent} />
      <path d="M74 30c14 0 18 26 8 36-6-2-10-12-12-20z" fill={accent} />
      <path d="M26 46c0-18 12-28 24-28s24 10 24 28-8 36-24 36-24-18-24-36z" />
      <ellipse cx="50" cy="65" rx="13" ry="10" />
      <ellipse cx="50" cy="60" rx="5" ry="3.5" fill={ink} stroke="none" />
      <circle cx="40" cy="47" r="3.5" fill={ink} stroke="none" />
      <circle cx="60" cy="47" r="3.5" fill={ink} stroke="none" />
      <path d="M47 73h6v4a3 3 0 0 1-6 0z" fill="#f87171" />
      <path d="M50 64v4c-2 3-5 3-7 1M50 68c2 3 5 3 7 1" fill="none" />
    </>
  ),
  paw: ({ accent }) => (
    <>
      <ellipse cx="26" cy="46" rx="8" ry="10" transform="rotate(-20 26 46)" />
      <ellipse cx="41" cy="30" rx="8" ry="10" transform="rotate(-6 41 30)" />
      <ellipse cx="59" cy="30" rx="8" ry="10" transform="rotate(6 59 30)" />
      <ellipse cx="74" cy="46" rx="8" ry="10" transform="rotate(20 74 46)" />
      <path
        d="M50 50c13 0 24 13 24 23 0 8-6 11-12 11-5 0-8-3-12-3s-7 3-12 3c-6 0-12-3-12-11 0-10 11-23 24-23z"
        fill={accent}
      />
    </>
  ),
  dice: ({ ink, accent }) => (
    <>
      <g transform="rotate(12 70 42)">
        <rect x="50" y="22" width="40" height="40" rx="8" fill={accent} />
        {[
          [60, 32],
          [80, 32],
          [60, 52],
          [80, 52],
        ].map(([cx, cy]) => (
          <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="3.5" fill="#fff" stroke="none" />
        ))}
      </g>
      <g transform="rotate(-14 34 58)">
        <rect x="12" y="36" width="44" height="44" rx="9" />
        {[
          [23, 47],
          [34, 58],
          [45, 69],
        ].map(([cx, cy]) => (
          <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="4" fill={ink} stroke="none" />
        ))}
      </g>
    </>
  ),
  controller: ({ ink, accent }) => (
    <>
      <path d="M30 34h40c12 0 18 10 20 26 2 14-4 22-12 22-6 0-10-6-14-12H36c-4 6-8 12-14 12-8 0-14-8-12-22 2-16 8-26 20-26z" />
      <path d="M30 45v16M22 53h16" fill="none" />
      <circle cx="66" cy="48" r="4.5" fill={accent} />
      <circle cx="75" cy="57" r="4.5" fill={ink} stroke="none" />
      <path d="M45 44h10" fill="none" />
    </>
  ),
  cards: ({ accent }) => (
    <>
      <rect x="18" y="24" width="38" height="54" rx="6" transform="rotate(-16 37 51)" fill={accent} />
      <rect x="32" y="20" width="38" height="54" rx="6" transform="rotate(2 51 47)" />
      <g transform="rotate(16 65 52)">
        <rect x="46" y="25" width="38" height="54" rx="6" />
        <path d="M65 40l3.5 7.5 8 1-6 5.5 1.5 8-7-4-7 4 1.5-8-6-5.5 8-1z" fill={accent} />
      </g>
    </>
  ),
  palette: ({ ink, accent }) => (
    <>
      <path d="M50 16c22 0 38 14 38 30 0 10-8 14-16 12-6-2-10 2-8 8 2 8-4 14-14 14-22 0-38-14-38-32s16-32 38-32z" />
      <circle cx="30" cy="42" r="6" fill={accent} stroke="none" />
      <circle cx="46" cy="29" r="6" fill="#60a5fa" stroke="none" />
      <circle cx="66" cy="31" r="6" fill={GOLD} stroke="none" />
      <circle cx="29" cy="61" r="6" fill="#34d399" stroke="none" />
      <path d="M66 90l24-34" fill="none" strokeWidth="6" />
      <path d="M90 56l5-11-10 6z" fill={ink} />
    </>
  ),
  frame: ({ accent }) => (
    <>
      <rect x="14" y="18" width="72" height="64" rx="4" />
      <rect x="23" y="27" width="54" height="46" rx="2" fill={accent} stroke="none" opacity="0.35" />
      <path d="M23 73l17-22 10 12 9-9 18 19z" fill={accent} />
      <circle cx="64" cy="40" r="5" />
    </>
  ),
  pencil: ({ ink, accent }) => (
    <>
      <path d="M12 84c10-10 18 6 28-2s16-8 24 0" fill="none" stroke={accent} />
      <g transform="rotate(38 52 48)">
        <rect x="44" y="12" width="16" height="56" rx="2" />
        <path d="M44 68h16l-8 16z" />
        <path d="M49.5 79l2.5 5 2.5-5z" fill={ink} />
        <rect x="44" y="6" width="16" height="10" rx="3" fill={accent} />
      </g>
      <path d="M22 22l3 7 7 3-7 3-3 7-3-7-7-3 7-3z" fill={accent} stroke="none" />
      <path d="M80 62l2 4.5 4.5 2-4.5 2-2 4.5-2-4.5-4.5-2 4.5-2z" fill={accent} stroke="none" />
    </>
  ),
  plush: ({ ink, accent }) => (
    <>
      <circle cx="29" cy="31" r="11" />
      <circle cx="71" cy="31" r="11" />
      <circle cx="29" cy="31" r="5" fill={accent} stroke="none" />
      <circle cx="71" cy="31" r="5" fill={accent} stroke="none" />
      <circle cx="50" cy="55" r="28" />
      <ellipse cx="50" cy="66" rx="11" ry="8" />
      <ellipse cx="50" cy="62" rx="4" ry="3" fill={ink} stroke="none" />
      <path d="M50 65v3" fill="none" />
      <circle cx="40" cy="51" r="3" fill={ink} stroke="none" />
      <circle cx="60" cy="51" r="3" fill={ink} stroke="none" />
      <circle cx="33" cy="62" r="4" fill={accent} stroke="none" opacity="0.6" />
      <circle cx="67" cy="62" r="4" fill={accent} stroke="none" opacity="0.6" />
    </>
  ),
  sofa: ({ accent }) => (
    <>
      <path d="M18 40c0-6 4-10 10-10h44c6 0 10 4 10 10v14H18z" />
      <path d="M50 31v23" fill="none" />
      <path d="M10 52a6 6 0 0 1 12 0v6h56v-6a6 6 0 0 1 12 0v22H10z" fill={accent} />
      <path d="M18 74v9M82 74v9" fill="none" />
    </>
  ),
  vase: ({ accent }) => (
    <>
      <path d="M50 22c2-8 10-12 14-12M50 22c-2-8-8-12-14-10" fill="none" />
      <ellipse cx="64" cy="10" rx="5" ry="3" fill={accent} stroke="none" />
      <ellipse cx="36" cy="12" rx="5" ry="3" fill={accent} stroke="none" />
      <path d="M38 22h24v8c0 4 12 12 12 30 0 16-10 26-24 26S26 76 26 60c0-18 12-26 12-30z" />
      <path d="M29 56h42M28 68h44" fill="none" stroke={accent} />
      <path d="M38 62h0M50 62h0M62 62h0" fill="none" stroke={accent} strokeWidth="5" />
    </>
  ),
  gift: ({ accent }) => (
    <>
      <rect x="20" y="44" width="60" height="40" rx="4" />
      <rect x="14" y="32" width="72" height="14" rx="4" />
      <path d="M50 34v48" fill="none" stroke={accent} strokeWidth="9" strokeLinecap="butt" />
      <path d="M50 32c-6-14-22-14-18-4 2 4 10 4 18 4zM50 32c6-14 22-14 18-4-2 4-10 4-18 4z" fill={accent} />
    </>
  ),
  christmas: () => (
    <>
      <rect x="44" y="76" width="12" height="11" rx="2" fill="#a16207" />
      <path d="M50 16l16 22h-8l14 20h-8l14 20H22l14-20h-8l14-20h-8z" fill="#4ade80" />
      <circle cx="42" cy="48" r="3.5" fill={RED} stroke="none" />
      <circle cx="58" cy="60" r="3.5" fill={RED} stroke="none" />
      <circle cx="44" cy="68" r="3.5" fill={GOLD} stroke="none" />
      <path d="M50 4l3 6.5 7 1-5 4.5 1.5 7-6.5-3.5-6.5 3.5 1.5-7-5-4.5 7-1z" fill={GOLD} />
    </>
  ),
  rings: ({ accent }) => (
    <>
      <circle cx="38" cy="60" r="20" fill="none" stroke="#f59e0b" strokeWidth="6" />
      <circle cx="62" cy="58" r="20" fill="none" stroke="#f59e0b" strokeWidth="6" />
      <path d="M52 30l5-8h10l5 8-10 12z" />
      <path d="M18 24c-5-3-7-6-5-8 2-2 4 0 5 2 1-2 3-4 5-2 2 2 0 5-5 8z" fill={accent} stroke="none" />
    </>
  ),
  balloons: ({ accent }) => (
    <>
      <path d="M38 61c-2 10 4 14 2 26M62 57c2 10-4 16-2 30" fill="none" />
      <ellipse cx="38" cy="40" rx="16" ry="20" fill={accent} />
      <path d="M35 60h6l-3 4z" fill={accent} />
      <ellipse cx="62" cy="36" rx="16" ry="20" />
      <path d="M59 56h6l-3 4z" />
      <path d="M30 30a8 8 0 0 1 6-6" fill="none" stroke="#fff" />
    </>
  ),
  tent: ({ accent }) => (
    <>
      <path d="M6 84h88" fill="none" />
      <path d="M12 84L44 26h12l32 58z" />
      <path d="M50 40L36 84h28z" fill={accent} />
      <path d="M50 26V12" fill="none" />
      <path d="M50 12l11 4-11 4z" fill={accent} />
      <circle cx="84" cy="22" r="6" />
    </>
  ),
  coins: ({ ink, accent }) => (
    <>
      <path d="M10 36l14-12 10 8 18-18M44 14h8v8" fill="none" />
      {[72, 62, 52].map((y) => (
        <g key={y}>
          <path d={`M14 ${y}v8a16 6 0 0 0 32 0v-8`} />
          <ellipse cx="30" cy={y} rx="16" ry="6" />
        </g>
      ))}
      <circle cx="70" cy="58" r="18" fill={accent} />
      <path d="M61 50l4 16 5-12 5 12 4-16M59 57h22" fill="none" stroke={ink} strokeWidth="3" />
    </>
  ),
  calendar: ({ ink, accent }) => (
    <>
      <rect x="18" y="24" width="64" height="58" rx="6" />
      <path d="M18 30a6 6 0 0 1 6-6h52a6 6 0 0 1 6 6v10H18z" fill={accent} />
      <path d="M34 16v14M66 16v14" fill="none" />
      {[52, 63, 74].flatMap((y) =>
        [30, 42, 54, 66].map((x) => <circle key={`${x}-${y}`} cx={x} cy={y} r="2.5" fill={ink} stroke="none" />),
      )}
      <circle cx="54" cy="63" r="7" fill="none" stroke={accent} />
    </>
  ),
  flower: ({ accent }) => (
    <>
      <path d="M50 52v34" fill="none" />
      <path d="M50 76c8-10 16-8 18-6-4 8-12 10-18 6z" fill={accent} />
      {[0, 72, 144, 216, 288].map((deg) => (
        <circle key={deg} cx="50" cy="24" r="9" transform={`rotate(${deg} 50 36)`} />
      ))}
      <circle cx="50" cy="36" r="7" fill={GOLD} />
    </>
  ),
  bag: ({ accent }) => (
    <>
      <path d="M36 38v-6a14 14 0 0 1 28 0v6" fill="none" />
      <path d="M22 38h56l-4 46H26z" />
      <path d="M24 50h52" fill="none" stroke={accent} strokeWidth="6" strokeLinecap="butt" />
      <path d="M50 76c-7-5-10-9-6-13 2-2 5-1 6 1 1-2 4-3 6-1 4 4 1 8-6 13z" fill={accent} stroke="none" />
    </>
  ),
  suitcase: ({ ink, accent }) => (
    <>
      <path d="M38 30v-8h24v8" fill="none" />
      <rect x="18" y="30" width="64" height="50" rx="8" />
      <path d="M34 31v48M66 31v48" fill="none" stroke={accent} strokeWidth="5" strokeLinecap="butt" />
      <circle cx="50" cy="52" r="7" fill={accent} stroke="none" />
      <circle cx="30" cy="87" r="4" fill={ink} stroke="none" />
      <circle cx="70" cy="87" r="4" fill={ink} stroke="none" />
    </>
  ),
  ticket: ({ accent }) => (
    <g transform="rotate(-10 50 50)">
      <path d="M12 30h76v13a7 7 0 0 0 0 14v13H12V57a7 7 0 0 0 0-14z" />
      <path d="M66 33v34" fill="none" strokeDasharray="4 5" />
      <path d="M38 38l3.5 7.5 8 1-6 5.5 1.5 8-7-4-7 4 1.5-8-6-5.5 8-1z" fill={accent} />
    </g>
  ),
}

function Decorations({ w, h, rand }) {
  // 큰 원 하나(그림 뒤), 작은 원 둘, 왼쪽 위 점 무늬
  const big = { cx: w * (0.55 + rand() * 0.3), cy: h * (0.2 + rand() * 0.6), r: h * (0.45 + rand() * 0.2) }
  const small = [0, 1].map(() => ({ cx: w * (0.05 + rand() * 0.4), cy: h * (0.15 + rand() * 0.7), r: h * (0.08 + rand() * 0.1) }))
  const dotX = w * (0.08 + rand() * 0.25)
  const dotY = h * (0.12 + rand() * 0.15)
  return (
    <g fill="#fff">
      <circle {...big} opacity="0.28" />
      {small.map((c, i) => (
        <circle key={i} {...c} opacity="0.22" />
      ))}
      {[0, 1, 2, 3].flatMap((col) =>
        [0, 1, 2].map((row) => (
          <circle key={`${col}-${row}`} cx={dotX + col * 10} cy={dotY + row * 10} r="1.8" opacity="0.55" />
        )),
      )}
    </g>
  )
}

export default function FairCover({ fair, size = 'card', className = '' }) {
  if (fair.image_url) {
    return <img src={fair.image_url} alt="" className={`h-full w-full object-cover ${className}`} />
  }
  const { w, h, motif: m, x } = SIZES[size]
  const palette = paletteFor(fair.category?.code)
  const motif = pickMotif(fair.title, fair.category?.code)
  const rand = seededRandom(fair.id)
  const gradientId = `cover-bg-${size}-${fair.id}`
  const Motif = MOTIFS[motif]
  const tilt = (rand() - 0.5) * 12 // -6° ~ 6°
  const mx = w * x - m / 2 + (rand() - 0.5) * w * 0.06
  const my = (h - m) / 2

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="xMidYMid slice"
      className={`h-full w-full ${className}`}
      aria-hidden="true"
      data-motif={motif}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={palette.from} />
          <stop offset="1" stopColor={palette.to} />
        </linearGradient>
      </defs>
      <rect width={w} height={h} fill={`url(#${gradientId})`} />
      <Decorations w={w} h={h} rand={rand} />
      <g transform={`translate(${mx} ${my}) scale(${m / 100}) rotate(${tilt} 50 50)`}>
        {/* 바닥 그림자 */}
        <ellipse cx="50" cy="92" rx="34" ry="4" fill={palette.ink} opacity="0.12" />
        <g
          fill="#fff"
          stroke={palette.ink}
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <Motif ink={palette.ink} accent={palette.accent} />
        </g>
      </g>
    </svg>
  )
}
