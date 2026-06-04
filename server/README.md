# E-Ink Dashboard Server

FastAPI server for an 800x480 e-ink dashboard. It stores dashboard data as JSON, renders a black-and-white PIL frame, and serves the packed raw frame consumed by the ESP32 firmware.

## Architecture

- `app.py`: FastAPI routes, control panel, render trigger, cron entrypoint.
- `models.py`: Pydantic request and data models.
- `storage.py`: JSON persistence in `../data/`.
- `fetcher.py`: async OpenWeatherMap fetcher for Beijing and local daily quote selection.
- `renderer.py`: 800x480 dashboard renderer.
- `renderer_recite.py`: full-screen recite mode renderer.
- `templates/control.html` and `static/style.css`: web control panel.

Generated data files live in the project-level `data/` directory:

- `ddl_data.json`
- `plan_data.json`
- `recite_data.json`
- `current.raw`
- `etag.txt`

## Setup

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py --host 0.0.0.0 --port 8646
```

Open `http://localhost:8646/` for the control panel.

To render once from cron:

```bash
cd server
python app.py --cron
```

To enable weather, edit `fetcher.py` and set `OPENWEATHER_API_KEY`.

## API Summary

- `GET /dashboard/status`: render status, DDL count, raw size, ETag.
- `GET /dashboard/current.raw`: raw frame bytes, with `ETag` and `304 Not Modified` support.
- `GET /dashboard/check`: current ETag for ESP32 polling.
- `POST /dashboard/trigger`: re-render immediately.
- `POST /dashboard/ddl`: replace DDL list with `{"items": [...]}`.
- `GET /dashboard/ddl/list`: return DDL list.
- `POST /dashboard/ddl/edit`: add, update, or delete one DDL item.
- `POST /dashboard/plan/today`: replace today's plan and exams.
- `POST /dashboard/plan/tick`: toggle one plan item's `done` value.
- `GET /dashboard/plan/list`: return today's plan.
- `POST /dashboard/recite`: set recite text and enter recite mode.
- `POST /dashboard/recite/clear`: clear recite mode.
- `GET /dashboard/recite/status`: recite text and active state.
- `GET /dashboard/health`: health check.
- `GET /dashboard/download/firmware`: download local ESP32 firmware if present.
- `GET /`: web control panel.

## Data Format

DDL item:

```json
{"name": "Math homework", "due_str": "2026-06-15", "days_left": 13, "priority": 0}
```

Plan:

```json
{
  "date": "2026-06-02",
  "items": [
    {"time": "08:30", "task": "Review notes", "subject": "Math", "done": false, "break": false},
    {"time": "10:00", "task": "Rest", "subject": "", "done": false, "break": true}
  ],
  "exams": [
    {"name": "Physics", "date": "2026-06-20", "days_left": 18}
  ]
}
```

Recite:

```json
{"text": "Paragraph one\n\nParagraph two"}
```

## ESP32 Pin Info

The firmware in `esp32/src/config.h` uses:

- `BUSY`: GPIO 14
- `CS`: GPIO 5
- `DC`: GPIO 21
- `RST`: GPIO 13
- `MOSI`: GPIO 17
- `SCLK`: GPIO 18
- `BUTTON`: GPIO 0

The ESP32 polls `/dashboard/check`, downloads `/dashboard/current.raw` when the ETag changes, and expects 96,000 bytes: 48,000 bytes for the black plane followed by 48,000 bytes for the color plane.
