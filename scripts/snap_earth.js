const { chromium } = require('playwright');

(async () => {
  const out = process.argv[2] || 'E:/Projects/NriGlobe/media/earth_preview_2026-09-15.png';
  const W = parseInt(process.argv[3], 10) || 1280;
  const H = parseInt(process.argv[4], 10) || 800;
  const doSel = process.argv[5] === 'sel';

  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--no-sandbox']
  });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 2 });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERR: ' + e.message));

  await page.goto('http://127.0.0.1:8731/index.html', { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('canvas', { timeout: 15000 });
  await page.waitForTimeout(4000);

  await page.screenshot({ path: out });
  console.log('SHOT_OK', out);

  if (doSel) {
    // 点击左侧第一个国家行，触发“选中即暂停 + 白色标记”
    const wantMid = process.argv[6] || null;
    const clicked = await page.evaluate((mid) => {
      const rows = document.querySelectorAll('.mrow');
      if (!rows.length) return null;
      let row = mid ? document.querySelector('.mrow[data-m="' + mid + '"]') : null;
      if (!row) row = rows[0];
      row.click();
      return row.getAttribute('data-m');
    }, wantMid);
    await page.waitForTimeout(4500); // 等 fly 动画 & 暂停生效
    const spinTxt = await page.evaluate(() => {
      const b = document.getElementById('btn-spin');
      return b ? b.textContent.trim() : '(nochip)';
    });
    const selOut = out.replace(/\.png$/, '_sel.png');
    await page.screenshot({ path: selOut });
    console.log('SHOT_SEL', selOut, 'mid=', clicked, 'spinChip=', spinTxt);
  }

  if (errors.length) console.log('PAGE_ERRORS:', errors.join(' | '));
  await browser.close();
})().catch(e => { console.error('SNAP_FAIL', e); process.exit(1); });
