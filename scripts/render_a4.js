// telegram/a4/latest.html → telegram/a4/latest.png (A4, 3배 해상도). 사용: node scripts/render_a4.js
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const dir = path.resolve(__dirname, '..', 'telegram', 'a4');
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 3 });
  await p.goto('file://' + path.join(dir, 'latest.html'));
  await p.waitForTimeout(500);
  console.log('font-size fit:', await p.evaluate(() => document.documentElement.dataset.fit));
  await p.screenshot({ path: path.join(dir, 'latest.png') });
  await b.close();
})();
