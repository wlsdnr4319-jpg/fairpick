import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http } from 'msw'
import { Route } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { uploadFairImage } from '../../api/admin'
import { renderApp } from '../../test/render'
import { API, json, server } from '../../test/server'
import AdminFairEdit from './AdminFairEdit'

// jsdom 의 File 을 MSW(undici)가 multipart 로 읽지 못해 업로드 함수만 바꿔 끼운다.
// 실제 multipart·검사·WebP 변환은 백엔드 tests/test_fair_images.py 가 확인한다
vi.mock('../../api/admin', async (importOriginal) => ({ ...(await importOriginal()), uploadFairImage: vi.fn() }))

const FAIR = {
  id: 7,
  title: '커피 엑스포',
  category: 'food',
  venue_id: 3,
  start_date: '2026-12-01',
  end_date: '2026-12-03',
  public_access: 'public',
  status: 'published',
  tags: [],
  image_url: null,
  verified_at: null,
}

const routes = <Route path="/admin/fairs/:fairId/edit" element={<AdminFairEdit />} />
const photo = (size = 1000) => new File([new Uint8Array(size)], 'booth.jpg', { type: 'image/jpeg' })

const UPLOADED = '/api/v1/uploads/fairs/7-abcdefghijklmnop.webp'

function endpoints(existing = FAIR) {
  uploadFairImage.mockReset().mockImplementation(async (id) => ({ ...existing, id, image_url: UPLOADED }))
  server.use(
    http.get(`${API}/categories`, () => json([{ code: 'food', name: '식음료' }])),
    http.get(`${API}/venues`, () => json([{ id: 3, name: '코엑스', region: '서울' }])),
    http.get(`${API}/tags`, () => json([])),
    http.get(`${API}/admin/fairs/:id`, () => json(existing)),
    http.delete(`${API}/admin/fairs/:id/image`, () => json({ ...existing, image_url: null })),
  )
  return uploadFairImage.mock.calls
}

const fileInput = () => screen.findByLabelText(/새 이미지/)

describe('표지 이미지', () => {
  beforeEach(() => vi.spyOn(window, 'confirm').mockReturnValue(true))

  it('이미지가 없으면 일러스트를 보여 주고, 권리 확인을 해야 올릴 수 있다', async () => {
    const uploads = endpoints()
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/7/edit' })

    await user.upload(await fileInput(), photo())
    expect(screen.getByText(/일러스트를 그리고 있어요/)).toBeInTheDocument()
    const button = screen.getByRole('button', { name: '이미지 올리기' })
    expect(button).toBeDisabled()

    await user.click(screen.getByLabelText('직접 찍었거나 사용 허락을 받은 이미지예요'))
    await user.click(button)

    expect(await screen.findByText('표지 이미지를 바꿨어요')).toBeInTheDocument()
    expect(uploads).toHaveLength(1)
    expect(uploads[0][0]).toBe(7)
    expect(uploads[0][1].name).toBe('booth.jpg')
    // 미리보기가 올린 이미지로 바뀌고, 지우기 버튼이 생긴다
    expect(document.querySelector(`img[src="${UPLOADED}"]`)).not.toBeNull()
    expect(screen.getByRole('button', { name: '이미지 지우기' })).toBeInTheDocument()
    // 다음 이미지를 올릴 때 다시 확인하게 체크를 푼다
    expect(screen.getByLabelText('직접 찍었거나 사용 허락을 받은 이미지예요')).not.toBeChecked()
  })

  it('5MB 가 넘는 파일은 보내지 않고 바로 알려 준다', async () => {
    const uploads = endpoints()
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/7/edit' })

    await user.upload(await fileInput(), photo(5 * 1024 * 1024 + 1))
    expect(screen.getByText('이미지는 5MB 이하만 올릴 수 있어요')).toBeInTheDocument()
    await user.click(screen.getByLabelText('직접 찍었거나 사용 허락을 받은 이미지예요'))
    expect(screen.getByRole('button', { name: '이미지 올리기' })).toBeDisabled()
    expect(uploads).toHaveLength(0)
  })

  it('서버가 거절하면 그 이유를 보여 준다', async () => {
    endpoints()
    uploadFairImage.mockRejectedValue({ response: { status: 422, data: { error: { code: 'IMAGE_INVALID', message: '이미지 파일을 읽을 수 없어요' } } } })
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/7/edit' })

    await user.upload(await fileInput(), photo())
    await user.click(screen.getByLabelText('직접 찍었거나 사용 허락을 받은 이미지예요'))
    await user.click(screen.getByRole('button', { name: '이미지 올리기' }))
    expect(await screen.findByText('이미지 파일을 읽을 수 없어요')).toBeInTheDocument()
  })

  it('지우면 일러스트 표지로 돌아간다', async () => {
    endpoints({ ...FAIR, image_url: UPLOADED })
    const user = userEvent.setup()
    renderApp(routes, { route: '/admin/fairs/7/edit' })

    await user.click(await screen.findByRole('button', { name: '이미지 지우기' }))
    expect(window.confirm).toHaveBeenCalled()
    expect(await screen.findByText('이미지를 지우고 일러스트 표지로 돌아갔어요')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
    expect(screen.queryByRole('button', { name: '이미지 지우기' })).not.toBeInTheDocument()
  })
})
