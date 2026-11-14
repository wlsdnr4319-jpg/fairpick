import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeFair } from '../test/fixtures'
import FairCover from './FairCover'

describe('박람회 표지', () => {
  it('이미지가 없으면 제목에 맞는 일러스트를 그린다 (화면 낭독기는 건너뜀)', () => {
    const { container } = render(<FairCover fair={makeFair({ title: '궁디팡팡 캣페스타', category: { code: 'pet', name: '반려동물' } })} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('data-motif', 'cat')
    expect(svg).toHaveAttribute('aria-hidden', 'true')
    expect(container.querySelector('img')).toBeNull()
  })

  it('같은 박람회는 몇 번 그려도 같은 그림', () => {
    const fair = makeFair({ id: 7, title: '2026 보드게임페스타', category: { code: 'leisure', name: '취미·레저' } })
    const a = render(<FairCover fair={fair} />).container.innerHTML
    const b = render(<FairCover fair={fair} />).container.innerHTML
    expect(a).toBe(b)
  })

  it('카드와 상세의 그라데이션 id 가 겹치지 않는다 (한 화면에 함께 있어도 색이 섞이지 않게)', () => {
    const fair = makeFair({ id: 9 })
    const card = render(<FairCover fair={fair} />).container.querySelector('linearGradient')
    const hero = render(<FairCover fair={fair} size="hero" />).container.querySelector('linearGradient')
    expect(card.id).not.toBe(hero.id)
  })

  it('관리자가 넣은 이미지가 있으면 그 이미지를 쓴다', () => {
    const { container } = render(<FairCover fair={makeFair({ image_url: 'https://img.example.com/a.jpg' })} />)
    expect(container.querySelector('img')).toHaveAttribute('src', 'https://img.example.com/a.jpg')
    expect(container.querySelector('svg')).toBeNull()
  })
})
