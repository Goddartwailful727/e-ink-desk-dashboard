# E-Ink Desk Dashboard

A server-rendered e-ink display system for desk productivity. Displays daily schedules, DDL countdowns, exam timelines, weather, and daily quotes on a 7.5-inch e-paper screen, wirelessly updated via WiFi.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-ESP32--S3-green.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow.svg)

## Features

- **Daily Schedule** — Time-blocked task list with done/undone status
- **DDL Countdown** — Deadlines sorted by urgency with D-N markers
- **Exam Countdown** — Upcoming exams with days-left indicators
- **Weather Panel** — Real-time weather via OpenWeatherMap API
- **Daily Quotes** — Rotating Chinese classical poetry (31 poems)
- **Recite Mode** — Full-screen text display for memorization
- **Photo Mode** — Upload any photo, auto-converted to e-ink bitmap with Floyd-Steinberg dithering, displayed full-screen until dismissed
- **Web Control Panel** — Browser-based CRUD for schedules and DDLs
- **Smart Rendering** — HTML→Puppeteer→1-bit bitmap pipeline with PIL fallback
- **ETag-based Polling** — ESP32 only re-downloads when content changes

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Server (Python + Node)                       │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  HTML/CSS/JS │───▶│  Puppeteer   │───▶│  1-bit Bitmap (.raw)  │  │
│  │  Dashboard   │    │  Screenshot  │    │  800×480, 48KB        │  │
│  └──────────────┘    └──────────────┘    └───────────┬───────────┘  │
│                                                      │              │
│  ┌──────────────┐    ┌──────────────┐               │              │
│  │  FastAPI     │───▶│  ETag Check  │◀──────────────┘              │
│  │  REST API    │    │  + Serve Raw │                              │
│  └──────────────┘    └──────┬───────┘                              │
│                             │                                      │
└─────────────────────────────┼──────────────────────────────────────┘
                              │  HTTP (WiFi)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ESP32-S3 + E-Ink                             │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐  │
│  │  WiFi        │───▶│  Poll /check │───▶│  Download .raw if new │  │
│  │  Manager     │    │  (10s int.)  │    │  + Display Frame      │  │
│  └──────────────┘    └──────────────┘    └───────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           Waveshare 7.5" e-Paper HAT (B) — 800×480          │    │
│  │           SPI interface via GxEPD2 library                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

The rendering pipeline works as follows:

1. **Data Input** — User pushes schedules/DDLs via Web UI or API
2. **HTML Rendering** — FastAPI serves an HTML dashboard page styled with CSS
3. **Screenshot** — Puppeteer (headless Chrome) captures the page at 800×480
4. **Bitmap Conversion** — The screenshot is converted to a 1-bit packed bitmap (black/white) + red layer
5. **Storage** — The raw bitmap is saved to `data/current.raw` with an ETag
6. **Polling** — ESP32 polls `/dashboard/check` every 10 seconds
7. **Display** — If the ETag changed, ESP32 downloads the raw bitmap and drives the e-ink display via SPI

If Puppeteer/Chrome is unavailable, the server falls back to a PIL-based renderer that draws directly to bitmap.

## Hardware Requirements

- **ESP32-S3** (tested with ESP32-S3 N16R8, QFN56 package)
- **Waveshare 7.5" e-Paper HAT (B)** — 800×480, three-color (black/red/white)
- **Waveshare e-Paper driver board**
- **Micro-USB cable** for power and flashing
- **Jumper wires** (6 SPI connections)

### Wiring (ESP32-S3 QFN56)

| Function | GPIO | Wire Color (suggested) |
|----------|------|------------------------|
| BUSY     | 14   | Orange                 |
| CS       | 5    | Blue                   |
| DC       | 21   | Green                  |
| RST      | 13   | White                  |
| MOSI     | 17   | Yellow                 |
| SCLK     | 18   | Red                    |

> **Note**: These pins are specific to the ESP32-S3 QFN56 variant. GPIO25 is not bonded out on QFN56. GPIO15/26 conflict with PSRAM bus. Adjust for your board variant.

### Power

The ESP32-S3 can power the e-ink display directly via USB. No external power supply is needed for the display itself — e-ink only draws current during refresh cycles.

## Server Setup

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for Puppeteer rendering — optional if using PIL fallback)
- **Google Chrome or Chromium** (for Puppeteer)

### Installation

```bash
# Clone the repository
git clone https://github.com/xiangyu-works/e-ink-desk-dashboard.git
cd e-ink-desk-dashboard

# Install Python dependencies
pip install -r server/requirements.txt

# Install Node.js dependencies (optional, for Puppeteer rendering)
npm install puppeteer-core
# Or for full Chromium:
# npm install puppeteer
```

### Configuration

Create a `.env` file or set environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `WEATHER_LAT` | Latitude for weather API | `39.9042` (Beijing) |
| `WEATHER_LON` | Longitude for weather API | `116.4074` (Beijing) |
| `OPENWEATHER_API_KEY` | Your OpenWeatherMap API key | *(empty — weather disabled)* |
| `CHROME_PATH` | Path to Chrome/Chromium binary | *(auto-detect)* |
| `SERVER_HOST` | Server bind address | `0.0.0.0` |
| `SERVER_PORT` | Server port | `8646` |

To get an OpenWeatherMap API key, sign up at [openweathermap.org](https://openweathermap.org/api) (free tier: 60 calls/min).

Edit `server/fetcher.py` to set your coordinates and API key directly:

```python
OPENWEATHER_API_KEY = "your-api-key-here"
BEIJING_LAT = 39.9042   # Change to your latitude
BEIJING_LON = 116.4074  # Change to your longitude
```

### Running

```bash
# Start the server (serves API + Web Control Panel)
cd server
python app.py

# Or with uvicorn directly:
uvicorn server.app:app --host 0.0.0.0 --port 8646

# Render once and exit (useful for cron jobs):
python app.py --cron
```

The web control panel will be available at `http://localhost:8646/`.

## Firmware Setup

### Prerequisites

- **PlatformIO** (VS Code extension or [CLI](https://platformio.org/install/cli))

### Configuration

1. Copy the example config and edit it for your network:

```bash
cp esp32/src/config.h.example esp32/src/config.h
```

2. Edit `esp32/src/config.h`:

```cpp
// WiFi credentials
static const char WIFI_SSID[] = "YourNetworkName";
static const char WIFI_PASS[] = "YourPassword";

// Server URL (must be reachable from the ESP32's network)
static const String SERVER_BASE = "http://your-server-ip:8646";
```

3. The PlatformIO configuration is in `esp32/platformio.ini`. Key settings:

```ini
[env:esp32-s3-devkitc-1]
platform = espressif32
board = esp32-s3-devkitc-1
framework = arduino
board_build.flash_mode = qio
board_build.flash_size = 16MB
board_build.psram = enable
board_build.psram_mode = opi
build_flags =
  -DBOARD_HAS_PSRAM
  -DARDUINO_USB_CDC_ON_BOOT=1
lib_deps =
  GxEPD2
```

### Build and Flash

```bash
cd esp32

# Build
pio run

# Flash via USB
pio run --target upload

# Monitor serial output
pio device monitor --baud 115200
```

### Important Notes

- **PSRAM must be enabled** (`board_build.psram = enable`) — frame buffers (48KB each for black and red layers) are allocated in PSRAM
- **Display updates must happen in `loop()`**, not `setup()` — the ESP32 watchdog timer (WDT) will reset the device if `setup()` takes too long
- **Flash config**: `qio` mode, 16MB size for ESP32-S3 N16R8
- **Pin conflicts**: On QFN56 packages, GPIO25 is not bonded out. GPIO15 and GPIO26 are used by the PSRAM bus — do not assign them to the display
- **USB CDC**: `ARDUINO_USB_CDC_ON_BOOT=1` enables serial over USB for monitoring

## API Reference

All endpoints are relative to the server base URL (e.g., `http://localhost:8646`).

### Display Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard/check` | Returns current ETag for change detection |
| `GET` | `/dashboard/current.raw` | Downloads the raw bitmap (supports ETag/304) |
| `GET` | `/dashboard/status` | Returns render status, DDL count, etag |
| `POST` | `/dashboard/trigger` | Force a re-render |
| `GET` | `/dashboard/health` | Health check |

### Plan (Daily Schedule) Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/dashboard/plan/today` | Push a full daily plan (items + exams) |
| `POST` | `/dashboard/plan/tick` | Toggle a task's done status by index |
| `POST` | `/dashboard/plan/edit` | Add, edit, or remove a plan item |
| `GET` | `/dashboard/plan/list` | Get the current plan |

### DDL (Deadline) Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/dashboard/ddl` | Push a full DDL list |
| `POST` | `/dashboard/ddl/edit` | Add, edit, or remove a DDL item |
| `GET` | `/dashboard/ddl/list` | Get current DDL list |

### Recite Mode Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/dashboard/recite` | Set recite text (full-screen mode) |
| `POST` | `/dashboard/recite/clear` | Clear recite mode |
| `GET` | `/dashboard/recite/status` | Check if recite mode is active |

### Photo Mode Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/dashboard/photo` | Upload a photo (multipart) — converts to e-ink bitmap and displays full-screen |
| `POST` | `/dashboard/trigger` | Force re-render — also exits photo mode and restores dashboard |
| `GET` | `/` | Web control panel (browser UI) |
| `GET` | `/epaper.html` | The HTML dashboard page (for Puppeteer) |

### Examples

**Check for updates (used by ESP32):**
```bash
curl http://localhost:8646/dashboard/check
# {"etag": "a1b2c3d4..."}
```

**Download raw bitmap:**
```bash
curl -H 'If-None-Match: "a1b2c3d4"' http://localhost:8646/dashboard/current.raw -o display.raw
# Returns 304 if unchanged, 200 with binary data if new
```

**Push a daily plan:**
```bash
curl -X POST http://localhost:8646/dashboard/plan/today \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"name": "Morning standup", "time": "09:00", "done": false},
      {"name": "Code review", "time": "14:00", "done": false}
    ],
    "exams": [
      {"name": "Calculus Final", "date": "2026-06-20", "days_left": 16}
    ]
  }'
```

**Toggle a task as done:**
```bash
curl -X POST http://localhost:8646/dashboard/plan/tick \
  -H "Content-Type: application/json" \
  -d '{"index": 0}'
```

**Add a DDL:**
```bash
curl -X POST http://localhost:8646/dashboard/ddl/edit \
  -H "Content-Type: application/json" \
  -d '{"action": "add", "item": {"name": "Project Report", "due_str": "2026-06-15"}}'
```

**Set recite text:**
```bash
curl -X POST http://localhost:8646/dashboard/recite \
  -H "Content-Type: application/json" \
  -d '{"text": "To be or not to be, that is the question."}'
```

**Upload a photo:**
```bash
curl -X POST http://localhost:8646/dashboard/photo \
  -F "photo=@photo.jpg"
```

## Customization

### Changing Display Size

The display dimensions are defined in multiple places:

1. **ESP32 firmware** (`esp32/src/config.h`):
   ```cpp
   static constexpr uint16_t DISPLAY_WIDTH = 800;
   static constexpr uint16_t DISPLAY_HEIGHT = 480;
   static constexpr size_t FRAME_BYTES = 48000; // WIDTH * HEIGHT / 8
   ```

2. **Puppeteer screenshot** (`screenshot.js`):
   ```js
   const WIDTH = 800;
   const HEIGHT = 480;
   ```

3. **HTML/CSS** (`epaper-dashboard/styles.css`):
   Adjust the viewport and layout dimensions to match.

4. **PIL renderer** (`server/renderer.py`):
   Update the canvas size constants.

### Adding Weather Provider

The weather integration lives in `server/fetcher.py`. To add a different provider:

1. Implement a new async function that returns the same dict structure
2. Replace the `fetch_weather()` call in `server/app.py`
3. Update the HTML template to render the new data format

### Modifying Quotes

Quotes are defined in the `POEMS` list in `server/fetcher.py`. Each entry is a tuple of `(text, author)`. The quote rotates daily based on `day_of_month % len(POEMS)`. Add or remove entries to customize.

### Adapting for Other Screens

To use a different Waveshare e-paper display:

1. Update `GxEPD2` display type in `esp32/src/display_manager.h`
2. Adjust width/height/frame bytes in `config.h`
3. Update the HTML layout in `epaper-dashboard/`
4. Recompile and flash

Supported by GxEPD2: 1.54", 2.13", 2.9", 4.2", 5.83", 7.5", and more.

## Project Structure

```
e-ink-desk-dashboard/
├── server/                     # Python FastAPI server
│   ├── app.py                  # Main application & API routes
│   ├── renderer.py             # PIL fallback renderer
│   ├── renderer_recite.py      # Recite mode renderer
│   ├── photo_renderer.py       # Photo-to-bitmap converter
│   ├── fetcher.py              # Weather API + quote rotation
│   ├── storage.py              # JSON file persistence
│   ├── models.py               # Pydantic data models
│   ├── push_plan.py            # CLI utility for pushing plans
│   ├── requirements.txt        # Python dependencies
│   ├── templates/
│   │   └── control.html        # Web control panel (Jinja2)
│   └── static/
│       └── style.css           # Control panel styles
├── epaper-dashboard/           # HTML/CSS/JS dashboard (rendered to bitmap)
│   ├── index.html              # Dashboard layout
│   ├── styles.css              # E-ink optimized styles
│   └── script.js               # Dynamic content loading
├── esp32/                      # ESP32 firmware (PlatformIO)
│   ├── platformio.ini          # Build configuration
│   └── src/
│       ├── config.h            # WiFi, server URL, pin definitions
│       ├── config.h.example    # Sanitized example config
│       ├── main.cpp            # Main loop: poll → download → display
│       ├── display_manager.h   # GxEPD2 display driver wrapper
│       ├── server_client.h     # HTTP client for API calls
│       └── wifi_manager.h      # WiFi connection with retry
├── screenshot.js               # Puppeteer screenshot service
├── data/                       # Runtime data (git-ignored except .gitkeep)
│   └── .gitkeep
├── README.md                   # This file
├── LICENSE                     # MIT License
└── .gitignore
```

## How It Works (Deep Dive)

### ETag-based Efficient Polling

The ESP32 polls the server every 10 seconds but only downloads new bitmap data when the content actually changes. This is achieved through ETag headers:

1. ESP32 calls `GET /dashboard/check` → receives `{"etag": "abc123"}`
2. Compares with stored ETag
3. If different, calls `GET /dashboard/current.raw` to download the new frame
4. If same, skips the download (saves bandwidth and flash wear)

### Rendering Pipeline

The server uses a two-tier rendering approach:

- **Primary**: Puppeteer (headless Chrome) renders the full HTML/CSS dashboard and captures a screenshot. This gives pixel-perfect output with full CSS support.
- **Fallback**: If Chrome is unavailable, PIL (Python Imaging Library) renders a simplified layout directly to bitmap. Less visually rich but always works.

### Photo Mode

Upload any photo to display it full-screen on the e-ink display. The server converts the image to a 1-bit bitmap optimized for e-paper:

1. **Upload** — `POST /dashboard/photo` with a multipart image file (JPEG, PNG, etc.)
2. **Conversion** — The server resizes and crops the image to 800×480, then applies Floyd-Steinberg dithering to convert grayscale to pure black-and-white pixels
3. **Display** — The resulting bitmap replaces the dashboard on the e-ink screen. The ESP32 detects the new ETag and downloads it on the next poll cycle
4. **Persistence** — Photo mode stays active until you explicitly dismiss it. While active, all data edits (plan, DDL, recite) update the stored data but skip re-rendering, preserving the photo on screen

To exit photo mode and return to the dashboard:

```bash
# Force re-render, which clears photo mode and restores the dashboard
curl -X POST http://localhost:8646/dashboard/trigger
```

Photo mode is useful as a digital photo frame, for displaying diagrams or notes, or simply for fun. The Floyd-Steinberg dithering produces surprisingly good results on e-ink — portraits, landscapes, and high-contrast images all render well.

### Three-Color Support

The Waveshare 7.5" HAT (B) supports three colors: black, red, and white. The raw bitmap format contains two layers:
- **Black layer** (48,000 bytes): 1 bit per pixel, 0 = black, 1 = white
- **Red layer** (48,000 bytes): 1 bit per pixel, 0 = red, 1 = transparent

Total frame size: 96,000 bytes transmitted per update.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Display shows nothing | Check SPI wiring; verify BUSY pin is correct |
| ESP32 resets during display update | Move display code from `setup()` to `loop()` |
| "Cannot allocate frame buffers" | Enable PSRAM in `platformio.ini` |
| Weather not showing | Set `OPENWEATHER_API_KEY` in fetcher.py |
| Puppeteer screenshot fails | Check `CHROME_PATH`; server falls back to PIL |
| GPIO conflict on QFN56 | Avoid GPIO15, GPIO25, GPIO26 (PSRAM/not bonded) |

## License

MIT — see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## Acknowledgments

- [GxEPD2](https://github.com/ZinggJM/GxEPD2) — Excellent e-paper library for ESP32
- [Waveshare](https://www.waveshare.com/) — e-Paper HAT hardware
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [Puppeteer](https://pptr.dev/) — Headless Chrome automation
- [Pillow](https://pillow.readthedocs.io/) — Python imaging library
