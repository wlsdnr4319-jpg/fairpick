import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { makeFair } from '../test/fixtures'
import FairCover from './FairCover'

const draw = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('박람회 표지', () => {
  it('이미지가 없으면 제목 주제에 맞는 예시 사진을 쓰고, 실제 행사 사진이 아님을 표시한다', () => {
    const { container } = draw(<FairCover fair={makeFair({ title: '궁디팡팡 캣페스타', category: { code: 'pet', name: '반려동물' } })} />)
    const img = container.querySelector('img')
    expect(img).toHaveAttribute('src', '/covers/cat-640.webp')
    expect(img).toHaveAttribute('srcset', expect.stringContaining('/covers/cat-1280.webp 1280w'))
    expect(img).toHaveAttribute('alt', '') // 장식 이미지: 화면 낭독기는 건너뜀
    expect(screen.getByText('예시 사진')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '출처' })).toBeNull() // 카드 안에는 링크를 두지 않는다
  })

  it('상세(hero)는 큰 사진과 사진 출처 링크를 보여 준다', () => {
    const { container } = draw(<FairCover fair={makeFair({ title: '서울커피엑스포' })} size="hero" credit />)
    expect(container.querySelector('img')).toHaveAttribute('src', '/covers/coffee-1280.webp')
    expect(screen.getByRole('link', { name: '출처' })).toHaveAttribute('href', '/credits')
  })

  it('여러 박람회가 같이 쓰는 카테고리 기본 사진은 박람회마다 두 장을 번갈아 쓴다', () => {
    const food = { code: 'food', name: '식음료' }
    const src = (id) => draw(<FairCover fair={makeFair({ id, title: '맛있는 박람회', category: food })} />).container.querySelector('img').getAttribute('src')
    expect(src(2)).toBe('/covers/plate-640.webp')
    expect(src(3)).toBe('/covers/plate2-640.webp')
    expect(src(4)).toBe('/covers/plate-640.webp')
  })

  it('예시 사진을 불러오지 못하면 일러스트로 바꾼다', () => {
    const { container } = draw(<FairCover fair={makeFair({ title: '2026 보드게임페스타' })} />)
    fireEvent.error(container.querySelector('img'))
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('svg')).toHaveAttribute('data-motif', 'dice')
    expect(screen.queryByText('예시 사진')).toBeNull()
  })

  it('같은 박람회는 몇 번 그려도 같은 표지', () => {
    const fair = makeFair({ id: 7, title: '2026 보드게임페스타', category: { code: 'leisure', name: '취미·레저' } })
    const a = draw(<FairCover fair={fair} />).container.innerHTML
    const b = draw(<FairCover fair={fair} />).container.innerHTML
    expect(a).toBe(b)
  })

  it('일러스트일 때 카드와 상세의 그라데이션 id 가 겹치지 않는다 (한 화면에 함께 있어도 색이 섞이지 않게)', () => {
    const fair = makeFair({ id: 9 })
    const card = draw(<FairCover fair={fair} />).container
    const hero = draw(<FairCover fair={fair} size="hero" />).container
    fireEvent.error(card.querySelector('img'))
    fireEvent.error(hero.querySelector('img'))
    expect(card.querySelector('linearGradient').id).not.toBe(hero.querySelector('linearGradient').id)
  })

  it('관리자가 올린 이미지가 있으면 그 이미지를 쓰고, 예시 표시는 없다', () => {
    const { container } = draw(<FairCover fair={makeFair({ image_url: '/api/v1/uploads/fairs/1-abc.webp' })} />)
    expect(container.querySelector('img')).toHaveAttribute('src', '/api/v1/uploads/fairs/1-abc.webp')
    expect(container.querySelector('svg')).toBeNull()
    expect(screen.queryByText('예시 사진')).toBeNull()
  })
})
