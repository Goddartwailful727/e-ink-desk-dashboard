/**
 * Puppeteer screenshot service for e-ink dashboard.
 *
 * Opens the HTML dashboard at http://localhost:8646/epaper.html,
 * screenshots at 800×480, converts to 1-bit bitmap format,
 * and saves as data/current.raw + data/etag.txt.
 *
 * Usage: node screenshot.js [--repeat]
 *   --repeat: keep running, re-render every 30 seconds
 */

const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CHROME_PATH = process.env.CHROME_PATH || '/usr/bin/google-chrome';
const DATA_DIR = path.join(__dirname, 'data');
const RAW_FILE = path.join(DATA_DIR, 'current.raw');
const ETAG_FILE = path.join(DATA_DIR, 'etag.txt');
const DASHBOARD_URL = 'http://localhost:8646/epaper.html';

const WIDTH = 800;
const HEIGHT = 480;
const FRAME_BYTES = WIDTH * HEIGHT / 8;

let browser = null;

async function launchBrowser() {
  if (browser) return browser;
  browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    args: [
      '--no-sandbox',
      '--headless=new',
      '--disable-gpu',
      '--disable-dev-shm-usage',
    ],
  });
  return browser;
}

async function render() {
  const b = await launchBrowser();
  const page = await b.newPage();

  try {
    await page.setViewport({ width: WIDTH, height: HEIGHT });
    await page.goto(DASHBOARD_URL, {
      waitUntil: 'networkidle0',
      timeout: 15000,
    });

    // Wait extra for JS to render data
    await page.waitForFunction(() => {
      const el = document.getElementById('todo-list');
      return el && el.children.length > 0;
    }, { timeout: 10000 }).catch(() => {
      console.log('[screenshot] Todo items not found, continuing anyway');
    });

    await new Promise(r => setTimeout(r, 500));
    await page.evaluate(() => document.fonts.ready);

    const screenshot = await page.screenshot({
      type: 'png',
      fullPage: false,
    });

    // Convert to 1-bit bitmap
    const { black, yellow } = convertToBitmap(screenshot);

    // Write files
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.writeFileSync(RAW_FILE, Buffer.concat([black, yellow]));

    const etag = crypto.createHash('md5').update(Buffer.concat([black, yellow])).digest('hex');
    fs.writeFileSync(ETAG_FILE, etag, 'utf-8');

    console.log(`[screenshot] Rendered ${WIDTH}x${HEIGHT}, etag=${etag}`);
    return etag;

  } catch (err) {
    console.error('[screenshot] Error:', err.message);
    throw err;
  } finally {
    await page.close();
  }
}

function convertToBitmap(pngData) {
  // Parse PNG and convert to 1-bit per pixel bitmap
  const { PNG } = require('pngjs');

  const png = PNG.sync.read(pngData);
  const black = Buffer.alloc(FRAME_BYTES);
  const yellow = Buffer.alloc(FRAME_BYTES);

  // Init yellow to all 1s (white)
  yellow.fill(0xFF);

  for (let y = 0; y < HEIGHT && y < png.height; y++) {
    for (let x = 0; x < WIDTH && x < png.width; x++) {
      const idx = (y * png.width + x) * 4;
      const r = png.data[idx];
      const g = png.data[idx + 1];
      const b = png.data[idx + 2];

      // Brightness: weighted RGB
      const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
      const isBlack = brightness < 128;

      const byteIdx = y * Math.floor(WIDTH / 8) + Math.floor(x / 8);
      const bitIdx = 7 - (x % 8);

      if (isBlack) {
        black[byteIdx] &= ~(1 << bitIdx);   // 0 = black
      } else {
        black[byteIdx] |= (1 << bitIdx);    // 1 = white
      }
    }
  }

  return { black, yellow };
}

async function shutdown() {
  if (browser) {
    await browser.close();
    browser = null;
  }
}

// Main
const REPEAT = process.argv.includes('--repeat');

if (REPEAT) {
  async function loop() {
    while (true) {
      try {
        await render();
      } catch (e) {
        console.error('[screenshot] Loop error:', e.message);
      }
      await new Promise(r => setTimeout(r, 30000));
    }
  }
  loop().catch(console.error);

  process.on('SIGINT', async () => { await shutdown(); process.exit(0); });
  process.on('SIGTERM', async () => { await shutdown(); process.exit(0); });
} else {
  render()
    .then(() => process.exit(0))
    .catch(() => process.exit(1));
}
