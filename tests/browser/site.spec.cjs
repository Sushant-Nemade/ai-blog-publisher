const { test, expect } = require('@playwright/test');

test.beforeEach(async ({ page }) => {
  await page.route('https://fonts.googleapis.com/**', route => route.abort());
  await page.route('https://fonts.gstatic.com/**', route => route.abort());
});

async function openArticle(page) {
  await page.goto('./index.html');
  await page.locator('.recent-card').first().click();
  await expect(page.locator('#postContent h2').first()).toBeVisible();
}

test('home, article, table, TOC and responsive framing', async ({ page }, testInfo) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await openArticle(page);
  await expect(page.locator('#postTitleH1')).toHaveText('Review Before Release');
  await expect(page.locator('#postContent table')).toBeVisible();
  await expect(page.locator('#postContent pre code')).toBeVisible();
  await expect(page.locator('#tocNav .toc-link')).toHaveCount(4);
  await expect(page.locator('hundefined')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Copy', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('article.png'), fullPage: true });
});

test('category search and empty state', async ({ page }) => {
  await page.goto('./category.html#cat=ml');
  await expect(page.locator('.blog-item')).toHaveCount(1);
  await page.locator('#searchInput').fill('nothing-matches-this');
  await expect(page.locator('.blog-item')).toHaveCount(0);
  await expect(page.locator('#emptyState')).toBeVisible();
  await page.locator('#searchInput').fill('Review');
  await expect(page.locator('.blog-item')).toHaveCount(1);
});

test('load failure offers retry and recovers', async ({ page }) => {
  let failed = false;
  await page.route('**/blogs/ml/articles.json', async route => {
    if (!failed) { failed = true; await route.fulfill({ status: 503, body: 'Unavailable' }); }
    else await route.continue();
  });
  await page.goto('./category.html#cat=ml');
  await expect(page.getByRole('alert')).toBeVisible();
  await page.getByRole('button', { name: 'Retry' }).click();
  await expect(page.locator('.blog-item')).toHaveCount(1);
});

test('Markdown and tags cannot execute script', async ({ page }) => {
  await page.route('**/blogs/ml/articles.json', async route => {
    const response = await route.fetch();
    const articles = await response.json();
    articles[0].tags = ['<img src=x onerror="window.injected=1">'];
    await route.fulfill({ response, json: articles });
  });
  await page.route('**/blogs/ml/*.md', route => route.fulfill({ body:
    '## Heading\n\n<img src=x onerror="window.injected=1"><script>window.injected=1</script>\n\n[unsafe](javascript:alert(1))' }));
  await openArticle(page);
  await expect(page.locator('#postTags img')).toHaveCount(0);
  await expect(page.locator('#postContent script')).toHaveCount(0);
  await expect(page.locator('#postContent [onerror]')).toHaveCount(0);
  await expect(page.locator('#postContent a[href^="javascript:"]')).toHaveCount(0);
  expect(await page.evaluate(() => window.injected)).toBeUndefined();
});

test('malformed post path fails safely', async ({ page }) => {
  await page.goto('./post.html#id=..%2Fprivate');
  await expect(page.getByRole('alert')).toBeVisible();
});