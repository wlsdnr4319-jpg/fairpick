import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Pagination from './Pagination'

const numbers = () =>
  screen
    .getAllByRole('button')
    .map((b) => b.textContent)
    .filter((t) => /^\d+$/.test(t))

describe('Pagination', () => {
  it('한 페이지뿐이면 그리지 않는다', () => {
    const { container } = render(<Pagination page={1} size={20} total={20} onChange={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('현재 페이지를 가운데 두고 최대 5개 번호를 보여 준다', () => {
    render(<Pagination page={6} size={10} total={100} onChange={() => {}} />)
    expect(numbers()).toEqual(['4', '5', '6', '7', '8'])
    expect(screen.getByRole('button', { name: '6' })).toHaveAttribute('aria-current', 'page')
  })

  it('끝 쪽에서는 마지막 5페이지를 보여 준다', () => {
    render(<Pagination page={10} size={10} total={100} onChange={() => {}} />)
    expect(numbers()).toEqual(['6', '7', '8', '9', '10'])
    expect(screen.getByRole('button', { name: '다음' })).toBeDisabled()
  })

  it('첫 페이지에서는 이전을 누를 수 없다', () => {
    render(<Pagination page={1} size={10} total={30} onChange={() => {}} />)
    expect(numbers()).toEqual(['1', '2', '3'])
    expect(screen.getByRole('button', { name: '이전' })).toBeDisabled()
  })

  it('누른 페이지 번호를 알려 준다', async () => {
    const onChange = vi.fn()
    render(<Pagination page={2} size={10} total={50} onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: '다음' }))
    await userEvent.click(screen.getByRole('button', { name: '5' }))
    expect(onChange.mock.calls).toEqual([[3], [5]])
  })
})
