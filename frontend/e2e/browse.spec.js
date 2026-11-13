import { expect, test } from '@playwright/test'

// 로그인하지 않은 방문자가 박람회를 찾아보는 흐름 (F-01 목록, F-02 상세, F-03 필터, F-04 검색, F-05 홈)
// 데이터: e2e_server 가 매번 넣는 시드 30건

test('홈에서 목록으로, 목록에서 상세로', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('이번 주말, 어떤 박람회 갈까요?')

  await page.getByRole('link', { name: '박람회 찾기' }).click()
  await expect(page).toHaveURL('/fairs')
  await expect(page.getByText('30개')).toBeVisible()

  // 첫 카드의 제목을 기억했다가 상세 화면 제목과 비교한다
  const firstCard = page.locator('main a[href^="/fairs/"]').first()
  const title = await firstCard.getByRole('heading').textContent()
  await firstCard.click()

  await expect(page).toHaveURL(/\/fairs\/\d+$/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(title)
})

test('검색어로 찾고, 주소를 그대로 열면 같은 결과', async ({ page }) => {
  await page.goto('/fairs')
  await page.getByLabel('검색어').fill('커피')
  await page.getByRole('button', { name: '검색' }).click()

  await expect(page).toHaveURL(/q=%EC%BB%A4%ED%94%BC/)
  // 새 결과가 올 때까지 이전 목록(30개)을 흐리게 보여 주므로, 바뀐 뒤에 센다
  await expect(page.getByText('30개')).toBeHidden()
  await expect(page.getByRole('heading', { name: '서울커피엑스포 2026' })).toBeVisible()
  const count = await page.getByText(/^\d+개$/).textContent()

  // 새로고침해도(주소 공유) 같은 목록
  await page.reload()
  await expect(page.getByLabel('검색어')).toHaveValue('커피')
  await expect(page.getByText(/^\d+개$/)).toHaveText(count)
})

test('카테고리 필터는 URL 에 남고 결과가 줄어든다', async ({ page }) => {
  await page.goto('/fairs')
  await expect(page.getByText('30개')).toBeVisible()

  await page.getByLabel('카테고리').selectOption({ label: '가족·육아' })

  await expect(page).toHaveURL(/category=family/)
  await expect(page.getByText('30개')).toBeHidden()
  await expect(page.getByRole('heading', { name: '글로벌 베이비페어' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '지스타 2026' })).toBeHidden()

  // 뒤로 가기로 필터 전 목록
  await page.goBack()
  await expect(page.getByText('30개')).toBeVisible()
})

test('없는 박람회는 404 화면', async ({ page }) => {
  await page.goto('/fairs/999999')
  await expect(page.getByRole('heading', { name: '페이지를 찾을 수 없어요' })).toBeVisible()
  await page.getByRole('link', { name: '홈으로 가기' }).click()
  await expect(page).toHaveURL('/')
})
