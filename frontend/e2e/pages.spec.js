import { expect, test } from '@playwright/test'

// 캘린더 (F-17), 통계 리포트 (F-19). 시드 데이터는 날짜가 고정이라 달을 주소로 정해 본다

test('캘린더: 날짜를 누르면 그날 행사 목록이 나오고, 누르면 상세로 간다', async ({ page }) => {
  await page.goto('/calendar?month=2026-11')
  await expect(page.getByRole('heading', { name: '2026년 11월' })).toBeVisible()
  const panel = page.getByRole('region', { name: /박람회 \d+개/ })
  const cafe = panel.getByRole('link', { name: /제25회 서울카페쇼/ })

  // 제25회 서울카페쇼: 2026-11-11 ~ 11-14. 10일에는 없고 12일에는 있다
  await page.getByRole('button', { name: /^11월 10일, 박람회/ }).click()
  await expect(page).toHaveURL('/calendar?month=2026-11&day=10')
  await expect(page.getByRole('heading', { name: /^11월 10일 \(화\)/ })).toBeVisible()
  await expect(cafe).toHaveCount(0)
  await page.getByRole('button', { name: /^11월 12일, 박람회/ }).click()
  await expect(cafe).toHaveCount(1)
  await cafe.click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('제25회 서울카페쇼')

  // 뒤로 가면 고른 날이 그대로 (주소에 남아 있다)
  await page.goBack()
  await expect(page.getByRole('button', { name: /^11월 12일, 박람회/ })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: '다음 달' }).click()
  await expect(page).toHaveURL('/calendar?month=2026-12')
  await expect(page.getByRole('heading', { name: '2026년 12월' })).toBeVisible()
  await expect(page.getByRole('link', { name: '제25회 서울카페쇼' })).toHaveCount(0)
})

test('통계: 요약 숫자와 차트를 그리고, 차트는 표로도 볼 수 있다', async ({ page }) => {
  await page.goto('/report')
  await expect(page.getByRole('heading', { level: 1, name: '박람회 통계' })).toBeVisible()
  await expect(page.getByRole('region', { name: '요약' })).toContainText(/\d+개/)

  const monthly = page.locator('section').filter({ has: page.getByRole('heading', { name: '2026년 월별 개최 수' }) })
  // jsdom 에서는 못 보는 실제 차트: 막대가 그려졌는지
  const chart = monthly.getByRole('application')
  await expect(chart).toBeVisible()
  await expect(chart.locator('.recharts-bar-rectangle').first()).toBeVisible()
  await expect(monthly).toContainText(/월에 가장 많이 열렸어요/)

  await monthly.getByRole('button', { name: '표로 보기' }).click()
  await expect(monthly.getByRole('table')).toBeVisible()
  await expect(monthly.getByRole('row')).toHaveCount(13) // 머리글 + 12개월
  await expect(monthly.getByRole('row').last()).toContainText('12월')

  const categories = page.locator('section').filter({ has: page.getByRole('heading', { name: '카테고리별 개최 수' }) })
  await expect(categories.getByRole('row', { name: /식음료/ })).toBeVisible()
})

// 휴대폰에서 화면이 옆으로 밀리지 않는지 (가로 스크롤이 생기면 글자·버튼이 잘려 보인다)
test('휴대폰: 주요 화면이 옆으로 넘치지 않는다', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile', '휴대폰 폭에서만 본다')
  await page.goto('/fairs')
  const detail = await page.getByRole('article').first().getByRole('link').first().getAttribute('href')

  for (const path of ['/', '/fairs', detail, '/calendar?month=2026-11', '/report', '/credits', '/login', '/signup']) {
    await page.goto(path)
    await expect(page.locator('main')).not.toBeEmpty()
    await page.waitForLoadState('networkidle')
    const { scroll, view } = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      view: document.documentElement.clientWidth,
    }))
    expect(scroll, `${path} 가로 넘침`).toBeLessThanOrEqual(view)
  }
})
