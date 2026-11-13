import { expect, test } from '@playwright/test'
import { logout, newAccount, openFairByTitle, responseOf, signup } from './helpers'

// 관람 노트·후기·좋아요 (F-14, F-15), 태그 투표 (F-16)
// 같은 박람회를 다른 테스트·화면 크기도 쓰므로, 내 후기는 고유한 메모로 찾고 투표 수는 '전보다 1 늘었는지'로 본다

const TITLE = '제25회 서울카페쇼'
const openFair = (page) => openFairByTitle(page, TITLE, '서울카페쇼')

test('관람 노트를 공개로 남기면 후기가 되고, 다른 회원이 좋아요를 누를 수 있다', async ({ page }, testInfo) => {
  const writer = newAccount(testInfo, 'w')
  const memo = `E2E 후기 ${testInfo.project.name} ${Date.now()}: 오전 10시 전에 가면 한산해요`
  await signup(page, writer)
  await openFair(page)

  const note = page.getByRole('main').locator('section, form').filter({ has: page.getByRole('heading', { name: '내 관람 노트' }) })
  await note.getByRole('button', { name: '다녀왔어요' }).click()
  await note.getByLabel('다녀온 날').fill('2026-11-12')
  await note.getByLabel('별점').selectOption({ label: '★★★★' })
  await note.getByPlaceholder(/다녀온 기록/).fill(memo)
  await note.getByLabel(/후기로 공개하기/).check()
  await note.getByRole('button', { name: '저장' }).click()

  await expect(note).toContainText('2026-11-12 · ★★★★ · 공개')
  const review = page.getByRole('listitem').filter({ hasText: memo })
  await expect(review).toContainText(`${writer.nickname} (나)`)

  // 다른 회원이 좋아요
  await logout(page)
  await signup(page, newAccount(testInfo, 'r'))
  await openFair(page)
  const like = page.getByRole('listitem').filter({ hasText: memo }).getByRole('button', { name: /♥/ })
  await expect(like).toHaveText('♥ 0')
  await expect(like).toHaveAttribute('aria-pressed', 'false')
  await like.click()
  await expect(like).toHaveText('♥ 1')
  await expect(like).toHaveAttribute('aria-pressed', 'true')

  // 새로고침해도 유지
  await page.reload()
  await expect(page.getByRole('listitem').filter({ hasText: memo }).getByRole('button', { name: /♥/ })).toHaveText('♥ 1')
})

test('나만 보기 노트는 후기에 나오지 않고, 지우면 처음 상태로 돌아간다', async ({ page }, testInfo) => {
  const memo = `E2E 비공개 메모 ${testInfo.project.name} ${Date.now()}`
  await signup(page, newAccount(testInfo, 'p'))
  await openFair(page)

  const note = page.getByRole('main').locator('section, form').filter({ has: page.getByRole('heading', { name: '내 관람 노트' }) })
  await note.getByRole('button', { name: '다녀왔어요' }).click()
  await note.getByPlaceholder(/다녀온 기록/).fill(memo)
  await note.getByRole('button', { name: '저장' }).click()

  await expect(note).toContainText('나만 보기')
  await expect(note).toContainText(memo)
  await expect(page.getByRole('listitem').filter({ hasText: memo })).toHaveCount(0)

  // 삭제는 확인 창을 거친다
  page.once('dialog', (d) => d.accept())
  await note.getByRole('button', { name: '고치기' }).click()
  const deleted = responseOf(page, 'DELETE', '')
  await note.getByRole('button', { name: '삭제' }).click()
  await deleted
  await expect(note.getByRole('button', { name: '다녀왔어요' })).toBeVisible()
  await expect(page.getByText(memo)).toHaveCount(0)
})

test('태그 투표는 로그인해야 하고, 누르면 표가 하나 늘어난다', async ({ page }, testInfo) => {
  await openFair(page)
  const tag = page.getByRole('button', { name: /^#이색/ })
  await expect(tag).toBeDisabled()
  await expect(page.getByRole('link', { name: '로그인하고 투표하기' })).toBeVisible()

  await signup(page, newAccount(testInfo, 't'))
  await openFair(page)
  const count = async () => Number((await tag.textContent()).replace(/\D/g, '') || 0)
  const before = await count()

  const voted = responseOf(page, 'PUT', '')
  await tag.click()
  await voted
  await expect(tag).toHaveAttribute('aria-pressed', 'true')
  await expect.poll(count).toBe(before + 1)

  await page.reload()
  await expect(tag).toHaveAttribute('aria-pressed', 'true')
})
