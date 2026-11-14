import { expect } from '@playwright/test'

// E2E 전용 관리자 (backend/app/scripts/e2e_server.py 가 매번 만든다. E2E DB 에만 있다)
export const ADMIN = { email: 'admin@e2e.example.com', password: 'e2e-admin-password' }

// 테스트마다 새 계정 (같은 DB 를 쓰는 다른 테스트·화면 크기와 겹치지 않게)
export function newAccount(testInfo, label = '') {
  const id = `${testInfo.project.name}${label}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`
  return { email: `e2e-${id}@example.com`, password: 'e2e-password-1', nickname: `테스터${id.slice(-5)}` }
}

// 휴대폰 화면에서는 사이드바가 ☰ 서랍 안에 있다. 데스크톱이면 아무것도 하지 않는다
export async function openMenu(page) {
  const button = page.getByRole('button', { name: '메뉴 열기' })
  if (await button.isVisible()) await button.click()
}

export async function closeMenu(page) {
  const button = page.getByRole('button', { name: '메뉴 닫기' })
  if (await button.isVisible()) await button.click()
}

// 로그인 상태 확인: 사이드바(휴대폰은 서랍)에 로그아웃 버튼이 보인다
// 로그인 직후엔 페이지가 바뀌면서 열어 둔 서랍이 닫힐 수 있어, 열기와 확인을 함께 다시 시도한다
export async function expectSignedIn(page, timeout = 15_000) {
  await expect(async () => {
    await openMenu(page)
    await expect(page.getByRole('button', { name: '로그아웃' })).toBeVisible({ timeout: 1_000 })
  }).toPass({ timeout })
  await closeMenu(page)
}

export async function signup(page, account) {
  await page.goto('/signup')
  await page.getByLabel('이메일').fill(account.email)
  await page.getByLabel('비밀번호 (8자 이상)').fill(account.password)
  await page.getByLabel('닉네임').fill(account.nickname)
  await page.getByLabel('만 14세 이상입니다').check()
  await page.getByRole('button', { name: '가입하기' }).click()
  // 비밀번호 해시(Argon2)를 가입·로그인에서 두 번 하므로 느린 PC 에선 몇 초 걸린다
  await expect(page).toHaveURL('/', { timeout: 20_000 })
  await expectSignedIn(page)
}

export async function login(page, { email, password }, next) {
  await page.goto(next ? `/login?next=${encodeURIComponent(next)}` : '/login')
  await page.getByLabel('이메일').fill(email)
  await page.getByLabel('비밀번호').fill(password)
  await page.getByRole('button', { name: '로그인', exact: true }).click()
  await expectSignedIn(page)
}

// 로그아웃 요청이 끝나기 전에 이동하면 아직 로그인 상태라 로그인 화면이 홈으로 돌려보낸다
export async function logout(page) {
  await openMenu(page)
  await page.getByRole('button', { name: '로그아웃' }).click()
  await expect(page.getByRole('link', { name: '로그인', exact: true })).toBeVisible()
}

// 화면이 먼저 바뀌는 요청(낙관적 업데이트 등)은 서버 응답까지 기다린 뒤 새로고침·이동한다
export const responseOf = (page, method, pathEnd) =>
  page.waitForResponse((r) => r.request().method() === method && new URL(r.url()).pathname.endsWith(pathEnd) && r.ok())

export async function openFairByTitle(page, title, query = title) {
  await page.goto(`/fairs?q=${encodeURIComponent(query)}`)
  await page.getByRole('heading', { name: title }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title)
}
