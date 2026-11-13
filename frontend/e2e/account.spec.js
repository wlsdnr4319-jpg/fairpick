import { expect, test } from '@playwright/test'
import { logout, newAccount, openFairByTitle, responseOf, signup } from './helpers'

// 회원 흐름 (F-06 회원, F-07 북마크): 가입 → 북마크 → 새로고침해도 로그인 유지 → 마이페이지 → 로그아웃

// 북마크 요청이 서버에 닿을 때까지 기다린다 (화면은 낙관적 업데이트로 먼저 바뀌므로 화면만 보고 새로고침하면 요청이 끊긴다)
const bookmarkSaved = (page, method) => responseOf(page, method, '/bookmark')

const TITLE = '서울커피엑스포 2026'
const openFair = (page) => openFairByTitle(page, TITLE, '서울커피엑스포')

test('가입하고 북마크하면 마이페이지에 모이고, 해제하면 빠진다', async ({ page }, testInfo) => {
  const account = newAccount(testInfo)
  await signup(page, account)

  await openFair(page)
  const main = page.getByRole('main')
  const saved = bookmarkSaved(page, 'PUT')
  await main.getByRole('button', { name: '북마크', exact: true }).click()
  await expect(main.getByRole('button', { name: '북마크 해제' })).toHaveAttribute('aria-pressed', 'true')
  await saved
  await expect(main.getByText('북마크 1명')).toBeVisible()

  // 액세스 토큰은 메모리에만 있다. 새로고침하면 리프레시 쿠키로 로그인이 복구돼야 한다
  await page.reload()
  await expect(main.getByRole('button', { name: '북마크 해제' })).toBeVisible()

  await page.goto('/mypage')
  await expect(page.getByRole('heading', { name: `${account.nickname}님의 북마크` })).toBeVisible()
  const card = main.locator('a', { has: page.getByRole('heading', { name: TITLE }) })
  await expect(card).toBeVisible()

  const removed = bookmarkSaved(page, 'DELETE')
  await card.getByRole('button', { name: '북마크 해제' }).click()
  await removed
  await page.reload()
  await expect(page.getByText('아직 북마크한 박람회가 없어요')).toBeVisible()
})

test('비로그인으로 북마크를 누르면 로그인 후 그 박람회로 돌아온다', async ({ page, context }, testInfo) => {
  const account = newAccount(testInfo)
  await signup(page, account)
  await logout(page)

  await openFair(page)
  const fairUrl = page.url()
  await page.getByRole('main').getByRole('button', { name: '북마크', exact: true }).click()

  await expect(page).toHaveURL(/\/login\?next=/)
  await page.getByLabel('이메일').fill(account.email)
  await page.getByLabel('비밀번호').fill(account.password)
  await page.getByRole('button', { name: '로그인', exact: true }).click()

  await expect(page).toHaveURL(fairUrl, { timeout: 15_000 })
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(TITLE)

  // 리프레시 토큰은 스크립트로 읽을 수 없는 httpOnly 쿠키
  const cookies = await context.cookies()
  const refresh = cookies.find((c) => c.httpOnly)
  expect(refresh, 'httpOnly 리프레시 쿠키').toBeTruthy()
  expect(await page.evaluate(() => document.cookie)).not.toContain(refresh.value)
})

test('로그인하지 않으면 마이페이지 대신 로그인 화면', async ({ page }) => {
  await page.goto('/mypage')
  await expect(page).toHaveURL('/login?next=%2Fmypage')
})

test('마이페이지에서 로그아웃하면 로그인 화면이 아니라 홈으로', async ({ page }, testInfo) => {
  await signup(page, newAccount(testInfo))
  await page.goto('/mypage')
  await logout(page)
  await expect(page).toHaveURL('/')
})

test('탈퇴하면 홈으로 가고, 공개 화면은 그대로 쓰이며, 같은 계정으로는 로그인할 수 없다', async ({ page }, testInfo) => {
  const account = newAccount(testInfo)
  await signup(page, account)
  await page.goto('/mypage/settings')

  page.once('dialog', (d) => d.accept())
  const withdrawn = responseOf(page, 'DELETE', '/me')
  await page.getByRole('button', { name: '탈퇴하기' }).click()
  await withdrawn
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('link', { name: '로그인', exact: true })).toBeVisible()

  // 탈퇴한 회원의 토큰이 메모리에 남으면 모든 요청이 401 이라 목록도 실패했다
  // 새로고침하면 메모리가 비므로 앱 안에서 이동해 본다
  await page.getByLabel('박람회 검색').fill('서울커피엑스포')
  await page.getByRole('button', { name: '검색', exact: true }).click()
  await expect(page.getByRole('heading', { name: TITLE })).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)

  await page.goto('/login')
  await page.getByLabel('이메일').fill(account.email)
  await page.getByLabel('비밀번호').fill(account.password)
  await page.getByRole('button', { name: '로그인', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page).toHaveURL('/login')
})

test('비밀번호가 틀리면 안내하고 로그인되지 않는다', async ({ page }, testInfo) => {
  const account = newAccount(testInfo)
  await signup(page, account)
  await logout(page)

  await page.goto('/login')
  await page.getByLabel('이메일').fill(account.email)
  await page.getByLabel('비밀번호').fill('wrong-password')
  await page.getByRole('button', { name: '로그인', exact: true }).click()

  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page).toHaveURL('/login')
})
