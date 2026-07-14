import { expect, test, type Page } from '@playwright/test'

async function setUiMode(page: Page, mode: 'classic' | 'minimal') {
  const login = await page.request.post('/api/v1/auth/login', { data: { email: 'visual@example.de', password: 'playwright-visual-password' } })
  expect(login.ok()).toBeTruthy()
  const tokens = await login.json()
  await page.goto('/')
  await page.evaluate((value) => localStorage.setItem('avento.auth.tokens', JSON.stringify(value)), tokens)
  await page.goto('/profil')
  const response = await page.evaluate(async (nextMode) => {
    const raw = localStorage.getItem('avento.auth.tokens')
    const tokens = raw ? JSON.parse(raw) as { access_token: string } : null
    return fetch('/api/v1/profile', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokens?.access_token ?? ''}` },
      body: JSON.stringify({ ui_mode: nextMode }),
    }).then((result) => result.status)
  }, mode)
  expect(response).toBe(200)
  await page.reload()
  await expect(page.getByRole('switch', { name: 'Minimal UI (Beta)' })).toBeVisible()
}

test('Beta-Toggle bestätigt, persistiert und stellt Classic wieder her', async ({ page, browser }) => {
  await setUiMode(page, 'classic')
  const toggle = page.getByRole('switch', { name: 'Minimal UI (Beta)' })
  await expect(toggle).not.toBeChecked()
  await toggle.click()
  const confirm = page.getByRole('dialog', { name: 'Minimal UI aktivieren?' })
  await expect(confirm).toBeVisible()
  await confirm.getByRole('button', { name: 'Abbrechen' }).click()
  await expect(toggle).not.toBeChecked()
  await toggle.click()
  await confirm.getByRole('button', { name: 'Beta aktivieren' }).click()
  await expect(page.getByRole('button', { name: 'Informationen zur Minimal UI Beta' })).toBeVisible()

  await page.reload()
  await expect(page.getByRole('button', { name: 'Informationen zur Minimal UI Beta' })).toBeVisible()

  const context = await browser.newContext({ storageState: await page.context().storageState(), colorScheme: 'dark' })
  const freshPage = await context.newPage()
  await freshPage.goto('/')
  await expect(freshPage.getByRole('heading', { name: /Hallo, Dimitri/ })).toBeVisible()
  await context.close()

  await page.goto('/profil')
  await page.getByRole('switch', { name: 'Minimal UI (Beta)' }).click()
  await expect(page.getByRole('button', { name: /Hellen Modus aktivieren|Dunklen Modus aktivieren/ })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Informationen zur Minimal UI Beta' })).toHaveCount(0)
})

test('Navigation, Badge-Dialog und 320-px-Grundstruktur bleiben bedienbar', async ({ page }) => {
  await setUiMode(page, 'minimal')
  await page.setViewportSize({ width: 320, height: 760 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /Hallo, Dimitri/ })).toBeVisible()
  await page.getByRole('button', { name: 'Menü öffnen' }).click()
  await page.getByRole('link', { name: 'Meilensteine' }).click()
  await expect(page.getByRole('heading', { name: 'Was du dir erfahren hast.' })).toBeVisible()
  await page.getByRole('button', { name: 'Informationen zur Minimal UI Beta' }).click()
  const dialog = page.getByRole('dialog', { name: 'Minimal UI · Beta' })
  await expect(dialog).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})

test('visuelle Referenzen für Classic und Minimal UI', async ({ page }) => {
  const viewports = [
    { name: 'desktop', width: 1440, height: 1000 },
    { name: 'tablet', width: 834, height: 1112 },
    { name: 'mobile', width: 390, height: 844 },
  ] as const

  await setUiMode(page, 'classic')
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /Hallo Dimitri/ })).toBeVisible()
    await expect(page).toHaveScreenshot(`classic-dashboard-${viewport.name}.png`, { fullPage: true })
  }

  await setUiMode(page, 'minimal')
  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/')
    await expect(page.getByRole('heading', { name: /Hallo, Dimitri/ })).toBeVisible()
    await expect(page).toHaveScreenshot(`minimal-dashboard-${viewport.name}.png`, { fullPage: true })
  }

  for (const viewport of [viewports[0], viewports[2]]) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/meilensteine')
    await expect(page.getByRole('heading', { name: 'Was du dir erfahren hast.' })).toBeVisible()
    await expect(page).toHaveScreenshot(`minimal-milestones-${viewport.name}.png`, { fullPage: true })
  }

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await page.getByRole('button', { name: 'Informationen zur Minimal UI Beta' }).click()
  await expect(page).toHaveScreenshot('minimal-beta-dialog-mobile.png')
})
