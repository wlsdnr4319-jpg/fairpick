import { expect, test } from '@playwright/test'
import { ADMIN, login, logout, newAccount, openMenu, signup } from './helpers'

// 관리자 흐름 (F-08 관리자, F-10 수집 검수). 관리자 계정과 검수 대기 항목은 e2e_server 가 넣어 둔다

test('박람회를 초안으로 등록 → 공개 → 숨김, 상태에 따라 공개 화면이 바뀐다', async ({ page }, testInfo) => {
  const title = `E2E 등록 박람회 ${testInfo.project.name} ${Date.now()}`
  await login(page, ADMIN)

  await openMenu(page)
  await page.getByRole('link', { name: '관리자 홈' }).click()
  await page.getByRole('link', { name: '새 박람회 등록' }).click()
  await page.getByLabel('제목').fill(title)
  await page.getByLabel('카테고리').selectOption({ label: '식음료' })
  await page.getByLabel('전시장').selectOption({ label: '코엑스 (서울)' })
  await page.getByLabel('시작일').fill('2027-05-01')
  await page.getByLabel('종료일').fill('2027-05-03')
  await page.getByLabel(/현장 입장료/).fill('0') // 0 = 무료 (비우면 '확인 중')
  await page.getByLabel('데이트 추천').check()
  await page.getByRole('button', { name: '저장' }).click()

  await expect(page.getByRole('status')).toHaveText('저장했어요')
  await expect(page).toHaveURL(/\/admin\/fairs\/\d+\/edit$/)
  const fairId = page.url().match(/fairs\/(\d+)\/edit/)[1]

  // 초안은 공개 목록·상세에 나오지 않는다
  await page.goto(`/fairs?q=${encodeURIComponent(title)}`)
  await expect(page.getByText('조건에 맞는 박람회가 없어요')).toBeVisible()
  await page.goto(`/fairs/${fairId}`)
  await expect(page.getByRole('heading', { name: '페이지를 찾을 수 없어요' })).toBeVisible()

  // 공개 + 정보 확인
  await page.goto(`/admin/fairs/${fairId}/edit`)
  await page.getByLabel('상태').selectOption('published')
  await page.getByLabel(/공식 사이트에서 정보를 확인했어요/).check()
  await page.getByRole('button', { name: '저장' }).click()
  await expect(page.getByRole('status')).toHaveText('저장했어요')
  await expect(page.getByText(/마지막 정보 확인:/)).toBeVisible()

  await page.getByRole('link', { name: '공개 화면 보기' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title)
  await expect(page.getByText('5.1(토) ~ 5.3(월)')).toBeVisible()
  await expect(page.getByText('무료', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '#데이트 추천' })).toBeVisible()
  await expect(page.getByText(/^정보 확인일/)).toBeVisible()

  // 숨김: 공개 화면에서 사라지고, 관리자 목록 '숨김' 에는 남는다
  await page.goto(`/admin/fairs/${fairId}/edit`)
  await page.getByLabel('상태').selectOption('hidden')
  await page.getByRole('button', { name: '저장' }).click()
  await expect(page.getByRole('status')).toHaveText('저장했어요')

  await page.goto(`/fairs/${fairId}`)
  await expect(page.getByRole('heading', { name: '페이지를 찾을 수 없어요' })).toBeVisible()
  await page.goto('/admin/fairs?status=hidden')
  await expect(page.getByRole('link', { name: title })).toBeVisible()
})

// 작은 PNG (단색 4x4). 서버가 실제로 열어 WebP 로 바꾸는지 보려고 진짜 이미지 바이트를 쓴다
const PNG_4X4 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAE0lEQVR4nGN81mPDAANMcBZeDgBVqgG2gGEi1gAAAABJRU5ErkJggg==',
  'base64',
)

test('표지 이미지를 올리면 공개 화면에 나오고, 지우면 일러스트로 돌아간다', async ({ page }, testInfo) => {
  const title = `E2E 표지 박람회 ${testInfo.project.name} ${Date.now()}`
  await login(page, ADMIN)
  await page.goto('/admin/fairs/new')
  await page.getByLabel('제목').fill(title)
  await page.getByLabel('카테고리').selectOption({ label: '식음료' })
  await page.getByLabel('전시장').selectOption({ label: '코엑스 (서울)' })
  await page.getByLabel('시작일').fill('2027-06-01')
  await page.getByLabel('종료일').fill('2027-06-02')
  await page.getByLabel('상태').selectOption('published')
  await page.getByRole('button', { name: '저장', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/fairs\/\d+\/edit$/)
  const fairId = page.url().match(/fairs\/(\d+)\/edit/)[1]

  const cover = page.getByRole('region', { name: '표지 이미지' })
  await cover.getByLabel(/새 이미지/).setInputFiles({ name: 'booth.png', mimeType: 'image/png', buffer: PNG_4X4 })
  await cover.getByLabel('직접 찍었거나 사용 허락을 받은 이미지예요').check()
  await cover.getByRole('button', { name: '이미지 올리기' }).click()
  await expect(cover.getByRole('status')).toHaveText('표지 이미지를 바꿨어요')

  // 공개 상세: 서버가 WebP 로 바꿔 둔 이미지를 실제로 받아 그린다
  await page.goto(`/fairs/${fairId}`)
  const img = page.locator('article img').first()
  await expect(img).toHaveAttribute('src', new RegExp(`^/api/v1/uploads/fairs/${fairId}-.+\\.webp$`))
  await expect.poll(() => img.evaluate((el) => el.complete && el.naturalWidth)).toBe(4)

  page.on('dialog', (d) => d.accept())
  await page.goto(`/admin/fairs/${fairId}/edit`)
  await cover.getByRole('button', { name: '이미지 지우기' }).click()
  await expect(cover.getByRole('status')).toHaveText('이미지를 지우고 일러스트 표지로 돌아갔어요')
  await page.goto(`/fairs/${fairId}`)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title)
  await expect(page.locator('article img')).toHaveCount(0)
})

test('수집 항목을 검수해 승인하면 공개되고, 반려하면 큐에서 빠진다', async ({ page }, testInfo) => {
  const approveTitle = `E2E 수집 디저트 페어 (${testInfo.project.name})`
  const rejectTitle = `E2E 수집 반려할 행사 (${testInfo.project.name})`
  await login(page, ADMIN)
  await page.goto('/admin/review')

  // 원본 제목이 정확히 같은 항목. 다른 항목의 '병합 후보' 에도 제목이 나올 수 있어 포함 여부로 찾지 않는다
  const queued = (title) => page.getByRole('listitem').filter({ has: page.getByText(title, { exact: true }) })
  const item = queued(approveTitle)
  await expect(item).toContainText('2027-03-05 ~ 2027-03-07') // 정규화 결과
  await item.getByRole('button', { name: '정보 채우고 승인' }).click()

  // 카테고리를 고르기 전에는 승인할 수 없다
  const approve = item.getByRole('button', { name: '승인해 공개' })
  await expect(approve).toBeDisabled()
  await item.getByLabel('카테고리').selectOption({ label: '식음료' })
  await item.getByLabel('일반인 관람').selectOption('public')
  await approve.click()
  await expect(queued(approveTitle)).toHaveCount(0)

  await queued(rejectTitle).getByRole('button', { name: '반려' }).click()
  await expect(queued(rejectTitle)).toHaveCount(0)

  // 승인한 항목은 공개 박람회가 되고, 반려한 항목은 어디에도 나오지 않는다
  await page.goto(`/fairs?q=${encodeURIComponent('E2E 수집')}`)
  await expect(page.getByRole('heading', { name: approveTitle })).toBeVisible()
  await expect(page.getByRole('heading', { name: rejectTitle })).toHaveCount(0)
  await page.getByRole('heading', { name: approveTitle }).click()
  await expect(page.getByText('일반인 관람 가능')).toBeVisible()
  await expect(page.getByText('코엑스 C홀 · 서울')).toBeVisible() // 원본 장소의 홀이 채워짐
})

test('장소를 못 맞춘 수집 항목은 전시장을 골라 승인하고, 그 장소 이름이 별칭으로 남는다', async ({ page }, testInfo) => {
  const title = `E2E 수집 장소 미확인 행사 (${testInfo.project.name})`
  await login(page, ADMIN)
  await page.goto('/admin/review')

  const item = page.getByRole('listitem').filter({ has: page.getByText(title, { exact: true }) })
  await expect(item).toContainText('매칭 실패')
  await item.getByRole('button', { name: '정보 채우고 승인' }).click()
  await item.getByLabel('카테고리').selectOption({ label: '문화·예술' })
  await expect(item.getByRole('button', { name: '승인해 공개' })).toBeDisabled()
  await expect(item.getByLabel('별칭', { exact: true })).toHaveValue(`E2E 컨벤션홀 ${testInfo.project.name}`)
  await item.getByLabel('전시장').selectOption({ label: 'SETEC (서울)' })
  await item.getByRole('button', { name: '승인해 공개' }).click()
  await expect(page.getByRole('listitem').filter({ has: page.getByText(title, { exact: true }) })).toHaveCount(0)

  await page.goto(`/fairs?q=${encodeURIComponent('장소 미확인')}`)
  await page.getByRole('heading', { name: title }).click()
  await expect(page.getByText('SETEC · 서울')).toBeVisible()
})

test('일반 회원은 관리자 화면을 쓸 수 없다', async ({ page }, testInfo) => {
  await signup(page, newAccount(testInfo, 'user'))
  await expect(page.getByRole('link', { name: '관리자 홈' })).toHaveCount(0)

  await page.goto('/admin/fairs/new')
  await expect(page.getByText('관리자만 이용할 수 있어요')).toBeVisible()

  // 화면을 우회해 API 를 직접 불러도 서버가 막는다 (토큰은 새로고침 복구로 받은 것과 같은 방식)
  const status = await page.evaluate(async () => {
    const { access_token } = await (await fetch('/api/v1/auth/refresh', { method: 'POST' })).json()
    const res = await fetch('/api/v1/admin/fairs', { headers: { Authorization: `Bearer ${access_token}` } })
    return res.status
  })
  expect(status).toBe(403)
  await logout(page)
})
