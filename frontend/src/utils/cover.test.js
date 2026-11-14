import { describe, expect, it } from 'vitest'
import { paletteFor, pickMotif, seededRandom } from './cover'

describe('표지 그림 고르기', () => {
  it.each([
    ['서울커피엑스포 2026', 'food', 'coffee'],
    ['제25회 서울 카페 쇼', 'food', 'coffee'], // 띄어쓰기가 달라도
    ['궁디팡팡 캣페스타', 'pet', 'cat'],
    ['2026 코리아 프리미어 도그쇼', 'pet', 'dog'],
    ['크리스마스 서울펫쇼', 'pet', 'paw'], // 동물이 크리스마스보다 먼저
    ['2026 대구크리스마스페어', 'lifestyle', 'christmas'],
    ['2026 보드게임페스타', 'leisure', 'dice'],
    ['Beaver Rocks 인디게임 & 컬처 페스티벌', 'tech', 'controller'],
    ['캐스크 카니발 2026', 'food', 'drinks'],
    ['코리아 라면페스타', 'food', 'noodles'],
    ['2026 경기미쌀디저트페스타', 'food', 'dessert'],
    ['고양 가구엑스포 & 홈앤리빙 더아트페스타', 'lifestyle', 'sofa'], // 가구가 아트보다 먼저
    ['2026 공예트렌드페어', 'culture', 'vase'],
    ['2026 국제아웃도어캠핑&레포츠페스티벌 더 파이널 시즌 PART 2', 'leisure', 'tent'],
    ['2026 명원세계차(茶)박람회', 'food', 'teapot'],
    ['2026 트래블 쇼', 'leisure', 'suitcase'],
    ['설맞이 명절선물전', 'lifestyle', 'gift'],
    ['솜프리마켓', 'lifestyle', 'plush'], // 솜인형이 마켓보다 먼저
    ['2026 소담마켓', 'lifestyle', 'bag'],
    ['Seoul Art Week', 'culture', 'palette'],
  ])('%s → %s', (title, category, motif) => {
    expect(pickMotif(title, category)).toBe(motif)
  })

  it('영어 키워드는 낱말 중간에서 맞추지 않는다', () => {
    expect(pickMotif('PART 2 시즌', 'leisure')).toBe('ticket') // 'art' 아님
    expect(pickMotif('Carpet Show', 'lifestyle')).toBe('bag') // 'pet' 아님
  })

  it('키워드가 없으면 카테고리 기본 그림', () => {
    expect(pickMotif('서울푸드 2026', 'food')).toBe('plate')
    expect(pickMotif('업라이징 페스타 Vol.2', 'culture')).toBe('frame')
    expect(pickMotif('38회 플래툰 컨벤션', 'leisure')).toBe('ticket')
    expect(pickMotif('무엇', 'unknown')).toBe('ticket')
  })

  it('카테고리 색이 없으면 회색', () => {
    expect(paletteFor('food').ink).toBe('#7c2d12')
    expect(paletteFor('nope').from).toBe('#e5e7eb')
  })

  it('같은 박람회 id 는 언제나 같은 장식, 다른 id 는 다른 장식', () => {
    const a1 = seededRandom(31)
    const a2 = seededRandom(31)
    const b = seededRandom(32)
    const first = [a1(), a1(), a1()]
    expect([a2(), a2(), a2()]).toEqual(first)
    expect(b()).not.toBe(first[0])
    first.forEach((v) => expect(v >= 0 && v < 1).toBe(true))
  })
})
