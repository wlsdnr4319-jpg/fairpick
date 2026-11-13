import { expect, test } from '@playwright/test'

// 회원 흐름 (F-06 회원, F-07 북마크): 가입 → 북마크 → 새로고침해도 로그인 유지 → 마이페이지 → 로그아웃

// 테스트마다 새 계정 (같은 DB 를 쓰는 다른 테스트·화면 크기와 겹치지 않게)
function newAccount(testInfo) {
  const id = `${testInfo.project.name}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`
  return { email: `e2e-${id}@example.com`, password: 'e2e-password-1', nickname: `테스터${id.slice(-4)}` }
}

async function signup(page, account) {
  await page.goto('/signup')
  await page.getByLabel('이메일').fill(account.email)
  await page.getByLabel('비밀번호 (8자 이상)').fill(account.password)
  await page.getByLabel('닉네임').fill(account.nickname)
  await page.getByLabel('만 14세 이상입니다').check()
  await page.getByRole('button', { name: '가입하기' }).click()
  // 비밀번호 해시(Argon2)를 가입·로그인에서 두 번 하므로 느린 PC 에선 몇 초 걸린다
  await expect(page).toHaveURL('/', { timeout: 20_000 })
  await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible()
}

// 로그아웃 요청이 끝나기 전에 이동하면 아직 로그인 상태라 로그인 화면이 홈으로 돌려보낸다
async function logout(page) {
  await page.getByRole('button', { name: '로그아웃' }).click()
  await expect(page.getByRole('link', { name: '로그인' })).toBeVisible()
}

// 북마크 요청이 서버에 닿을 때까지 기다린다 (화면은 낙관적 업데이트로 먼저 바뀌므로 화면만 보고 새로고침하면 요청이 끊긴다)
const bookmarkSaved = (page, method) =>
  page.waitForResponse((r) => r.url().endsWith('/bookmark') && r.request().method() === method && r.ok())

const TITLE = '서울커피엑스포 2026'

async function openFair(page, title = TITLE) {
  await page.goto(`/fairs?q=${encodeURIComponent('서울커피엑스포')}`)
  await page.getByRole('heading', { name: title }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title)
}

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
