/* Capture reproducible H08 Chrome mobile-size simulation from a loopback fixture. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function arg(name) {
  const i = process.argv.indexOf('--' + name);
  if (i < 0 || !process.argv[i + 1]) throw new Error('Missing --' + name);
  return process.argv[i + 1];
}

async function main() {
  const base = arg('base');
  const output = path.resolve(arg('output'));
  const chrome = arg('chrome');
  const playwright = require(arg('playwright-module'));
  if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw new Error('Loopback HTTP fixture required');
  if (!fs.existsSync(chrome)) throw new Error('Chrome executable missing');
  if (fs.existsSync(output)) throw new Error('Output directory already exists');
  fs.mkdirSync(output, { recursive: true });

  const captures = [];
  const browser = await playwright.chromium.launch({ executablePath: chrome, headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1, isMobile: true, hasTouch: true, locale: 'zh-TW' });
  const page = await context.newPage();
  const started = new Date().toISOString();
  async function shot(file, label, environment, result, status = 200) {
    const dest = path.join(output, file);
    await page.screenshot({ path: dest, animations: 'disabled' });
    const bytes = fs.readFileSync(dest);
    const width = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth }));
    captures.push({ file, label, at_utc: new Date().toISOString(), url: page.url(),
      viewport_css: page.viewportSize(), status, environment, result,
      horizontal_overflow: width.scroll > width.client, scroll_width_css: width.scroll,
      sha256: crypto.createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length,
      physical_phone: false, native_ios_keyboard: false, human_signoff: false });
  }
  async function goto(url, expected = 200) {
    const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 });
    if (response?.status() !== expected) throw new Error(url + ' returned ' + response?.status());
  }

  try {
    const metaResponse = await context.request.get(base + '/__h08_fixture_meta');
    if (!metaResponse.ok()) throw new Error('Local fixture unavailable');
    const meta = await metaResponse.json();
    if (meta.scope !== 'loopback mongomock visual fixture') throw new Error('Wrong fixture scope');

    await goto(base + '/product/' + meta.product_id);
    await page.locator('select[name="sku_id"]').selectOption({ index: 1 });
    await page.locator('input[name="quantity"]').focus();
    await page.locator('input[name="quantity"]').scrollIntoViewIfNeeded();
    await shot('S03-product-portrait-focus.png', 'S03 SKU/quantity portrait focus', 'localhost mongomock fixture',
      'Selected disposable SKU and focused quantity field; no physical keyboard');
    await page.setViewportSize({ width: 844, height: 390 });
    await page.locator('select[name="sku_id"]').scrollIntoViewIfNeeded();
    await shot('S03-product-landscape.png', 'S03 product landscape', 'localhost mongomock fixture',
      'Same product page at landscape CSS viewport');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('input[name="quantity"]').fill('0');
    await page.locator('input[name="quantity"]').scrollIntoViewIfNeeded();
    const quantityInvalid = await page.locator('input[name="quantity"]').evaluate(el => !el.checkValidity());
    if (!quantityInvalid) throw new Error('Quantity 0 did not trigger form validity check');
    await page.locator('input[name="quantity"]').evaluate(el => el.reportValidity());
    await shot('S03-invalid-quantity.png', 'S03 invalid quantity', 'localhost mongomock fixture',
      'Quantity 0 rejected by native HTML validity; no cart write');

    await goto(base + '/auth/login');
    await page.locator('input[name="email"]').fill('wrong@example.invalid');
    await page.locator('input[name="password"]').fill('wrong-local-fixture');
    await page.getByRole('button', { name: '登入' }).click();
    if (!(await page.locator('body').innerText()).includes('帳號或密碼不正確'))
      throw new Error('Invalid login error did not render');
    await shot('S04-invalid-login.png', 'S04 invalid login', 'localhost mongomock fixture',
      'Fake invalid credentials rejected with generic error');
    await page.locator('input[name="email"]').focus();
    await shot('S04-login-email-focus.png', 'S04 email focus', 'localhost mongomock fixture',
      'Desktop Chrome focus only; no iOS software keyboard');

    await goto(base + '/auth/login');
    await page.locator('input[name="email"]').fill('h08-sim@example.invalid');
    await page.locator('input[name="password"]').fill('h08-disposable-local-fixture');
    await page.getByRole('button', { name: '登入' }).click();
    if ((await page.locator('body').innerText()).includes('帳號或密碼不正確'))
      throw new Error('Local fixture login failed');
    await goto(base + '/product/' + meta.product_id);
    await page.locator('select[name="sku_id"]').selectOption({ index: 1 });
    await page.getByRole('button', { name: '加入購物車' }).click();
    if (!(await page.locator('body').innerText()).includes('購物車估計合計'))
      throw new Error('Local cart did not show added item');
    await shot('S05-cart-portrait.png', 'S05 cart portrait', 'localhost mongomock fixture',
      'One disposable SKU in cart, no production data');
    await page.setViewportSize({ width: 844, height: 390 });
    await shot('S05-cart-landscape.png', 'S05 cart landscape', 'localhost mongomock fixture',
      'Same cart at landscape CSS viewport');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole('button', { name: /建立示範訂單/ }).click();
    if (!(await page.locator('body').innerText()).includes('示範訂單'))
      throw new Error('Local demo order confirmation missing');
    await shot('S05-demo-order.png', 'S05 demo order', 'localhost mongomock fixture',
      'Disposable no-payment order; not a real MongoDB transaction');

    let publicStatus = null;
    let publicError = null;
    if (process.argv.includes('--public-url')) {
      const publicUrl = arg('public-url');
      if (!/^https:\/\/vibecart-llmai\.web\.app\/?$/.test(publicUrl))
        throw new Error('Unexpected public URL');
      const publicPage = await context.newPage();
      try {
        const response = await publicPage.goto(publicUrl, { waitUntil: 'domcontentloaded', timeout: 18000 });
        publicStatus = response?.status() ?? null;
        const file = 'S00-public-site-readback.png';
        const dest = path.join(output, file);
        await publicPage.screenshot({ path: dest, animations: 'disabled' });
        const bytes = fs.readFileSync(dest);
        captures.push({ file, label: 'Current public URL readback', at_utc: new Date().toISOString(),
          url: publicPage.url(), viewport_css: publicPage.viewportSize(), status: publicStatus,
          environment: 'public Firebase Hosting; current readback only',
          result: 'HTTP status at capture time; not proof of 2026-10-18 physical test',
          sha256: crypto.createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length,
          physical_phone: false, native_ios_keyboard: false, human_signoff: false });
      } catch (error) {
        publicError = String(error).slice(0, 250);
      } finally {
        await publicPage.close();
      }
    }

    const report = { schema_version: 1, started_at_utc: started, finished_at_utc: new Date().toISOString(),
      status: 'passed', scope: 'Chrome headless mobile-size simulation on localhost mongomock',
      public_url_status: publicStatus, public_capture_error: publicError,
      physical_phone: false, native_ios_keyboard: false,
      remote_acceptance: false, atlas_accessed: false, ren_named_receipt: false, captures };
    fs.writeFileSync(path.join(output, 'capture-records.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({ status: report.status, captures: captures.length, output }));
  } finally {
    await browser.close();
  }
}

main().catch(error => { console.error(error.stack || String(error)); process.exitCode = 1; });
