// telegram/cards/card-N.html → card-N.png (1080×1350, 2배 해상도). 사용: node scripts/render_cards.js
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const dir = path.resolve(__dirname, '..', 'telegram', 'cards');
  const files = fs.readdirSync(dir).filter(f => /^card-\d+\.html$/.test(f)).sort();
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 2 });
  for (const f of files) {
    await p.goto('file://' + path.join(dir, f));
    await p.waitForTimeout(300);
    console.log(f, 'font-size fit:', await p.evaluate(() => document.documentElement.dataset.fit));
    await p.screenshot({ path: path.join(dir, f.replace('.html', '.png')) });
  }
  await b.close();
})();
