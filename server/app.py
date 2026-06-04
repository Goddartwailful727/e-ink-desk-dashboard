from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from . import fetcher, photo_renderer, renderer, storage
    from .models import DDLItem, DDLListBody, PlanItem, PlanPushBody
except ImportError:
    import fetcher
    import photo_renderer
    import renderer
    
    import storage
    from models import DDLItem, DDLListBody, PlanItem, PlanPushBody


BASE_DIR = Path(__file__).resolve().parent
RAW_PATH = storage.DATA_DIR / "current.raw"
DATA_ETAG_PATH = storage.DATA_DIR / "data_etag.txt"
PHOTO_ETAG_PATH = storage.DATA_DIR / "photo_etag.txt"
FIRMWARE_CANDIDATES = [
    BASE_DIR.parent / "esp32/.pio/build/esp32dev/firmware.bin",
    BASE_DIR.parent / "esp32/.pio/build/esp32-s3-devkitc-1/firmware.bin",
    BASE_DIR.parent / "esp32/firmware.bin",
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_PATH.exists():
        await render_once()
    yield


app = FastAPI(title="E-Ink Dashboard Server", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _dump_model(model) -> dict[str, Any]:
    return model.model_dump(by_alias=True)


def _data_etag() -> str:
    """Stable ETag based on actual content data, not rendered bitmap."""
    plan = storage.get_plan()
    ddl_items = storage.get_ddl_items()
    exams = plan.get("exams", [])
    # 动态重算 days_left，让 ETag 随日期变化
    _recalc_days_left(ddl_items)
    _recalc_days_left(exams)
    data = ddl_items + plan.get("items", []) + exams
    data += [storage.get_recite_text()]
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode()).hexdigest()


def _stored_data_etag() -> str:
    if DATA_ETAG_PATH.exists():
        return DATA_ETAG_PATH.read_text(encoding="utf-8").strip()
    return ""


def _write_data_etag(etag: str) -> None:
    storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_ETAG_PATH.write_text(etag, encoding="utf-8")


def _photo_etag() -> str:
    if PHOTO_ETAG_PATH.exists():
        return PHOTO_ETAG_PATH.read_text(encoding="utf-8").strip()
    return ""


def _write_photo_etag(etag: str) -> None:
    storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHOTO_ETAG_PATH.write_text(etag, encoding="utf-8")


def _clear_photo_mode() -> None:
    try:
        PHOTO_ETAG_PATH.unlink()
    except FileNotFoundError:
        pass


def _photo_active() -> bool:
    """Check if photo mode is currently active."""
    return PHOTO_ETAG_PATH.exists()


def _etag() -> str:
    # Use the bitmap-based etag (updated on each render)
    bitmap_etag = storage.DATA_DIR / "etag.txt"
    if bitmap_etag.exists():
        return bitmap_etag.read_text(encoding="utf-8").strip()
    return _data_etag()


def _status() -> dict[str, Any]:
    stat = RAW_PATH.stat() if RAW_PATH.exists() else None
    return {
        "ok": RAW_PATH.exists(),
        "render_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds") if stat else "",
        "ddl_count": len(storage.get_ddl_items()),
        "raw_size": stat.st_size if stat else 0,
        "etag": _etag(),
    }


async def _payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    form = await request.form()
    return dict(form)


def _item_from_payload(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("item"), dict):
        return data["item"]
    return {
        "name": data.get("name", ""),
        "due_str": data.get("due_str") or data.get("date") or "",
        "days_left": data.get("days_left"),
        "priority": data.get("priority", 0),
    }


def _normalize_ddl_item(item: dict[str, Any]) -> dict[str, Any]:
    raw = dict(item)
    if "due_str" not in raw and "date" in raw:
        raw["due_str"] = raw.get("date", "")
    if raw.get("days_left") in ("", None):
        raw["days_left"] = _days_from_date(raw.get("due_str", ""))
    return _dump_model(DDLItem.model_validate(raw))


def _normalize_plan_item(item: dict[str, Any]) -> dict[str, Any]:
    return _dump_model(PlanItem.model_validate(item))


def _days_from_date(value: str) -> int | None:
    if not value:
        return None
    # 支持完整日期 + 仅月/日的短格式（自动补当前年份）
    year = date.today().year
    for fmt, template in (
        ("%Y-%m-%d", None),
        ("%Y/%m/%d", None),
        ("%m/%d", f"%Y/{value}"),
        ("%m-%d", f"%Y-{value}"),
    ):
        try:
            if template is not None:
                # 短格式：把月/日字符串拼到当前年份上再解析
                parsed = datetime.strptime(f"{year}-{value}" if fmt == "%m-%d" else f"{year}/{value}", 
                                           "%Y-%m-%d" if fmt == "%m-%d" else "%Y/%m/%d").date()
            else:
                parsed = datetime.strptime(value, fmt).date()
            return (parsed - date.today()).days
        except ValueError:
            pass
    # 兜底：处理 "6月10日" / "06月10" 等中文格式
    import re
    m = re.match(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日?", value)
    if m:
        try:
            parsed = date(year, int(m.group(1)), int(m.group(2)))
            return (parsed - date.today()).days
        except ValueError:
            pass
    return None


def _recalc_days_left(items: list[dict[str, Any]]) -> None:
    """原地重算列表中每个 item 的 days_left（只要有 due_str / date 就按今天算）。"""
    for item in items:
        due = item.get("due_str") or item.get("date") or ""
        if due:
            fresh = _days_from_date(due)
            if fresh is not None:
                item["days_left"] = fresh


async def build_data() -> dict[str, Any]:
    now = datetime.now()
    plan = storage.get_plan()
    ddl_items = storage.get_ddl_items()
    exams = plan.get("exams", [])
    # 渲染/轮询时动态刷新 days_left，让墨水屏显示始终准确
    _recalc_days_left(ddl_items)
    _recalc_days_left(exams)
    return {
        "ddl": ddl_items,
        "plan": plan,
        "exams": exams,
        "weather": await fetcher.fetch_weather(),
        "quote": fetcher.get_quote(now),
        "recite": storage.get_recite_text(),
        "now": now,
    }


async def _run_puppeteer(script_path: Path):
    """Run Puppeteer screenshot in a thread pool to avoid blocking the event loop."""
    import subprocess as _subprocess
    return await asyncio.to_thread(
        _subprocess.run,
        ["node", str(script_path)],
        capture_output=True, text=True, timeout=30,
        cwd=script_path.parent,
    )


async def render_once() -> dict[str, Any]:
    """Render dashboard via Puppeteer screenshot, fallback to PIL."""
    import subprocess
    script_path = BASE_DIR.parent / "screenshot.js"
    try:
        result = await _run_puppeteer(script_path)
        if result.returncode == 0:
            etag = _etag()
            _write_data_etag(etag)
            _clear_photo_mode()
            status = _status()
            status["etag"] = etag
            return status
        else:
            print(f"[render] Puppeteer error: {result.stderr}")
            raise RuntimeError(f"Puppeteer failed: {result.stderr}")
    except Exception as e:
        print(f"[render] Fallback to PIL: {e}")
        data = await build_data()
        black, yellow, _bitmap_etag = renderer.render(data)
        renderer.save_frame(black, yellow)
        etag = _data_etag()
        _write_data_etag(etag)
        _clear_photo_mode()
        status = _status()
        status["etag"] = etag
        return status


@app.get("/dashboard/status")
async def dashboard_status() -> dict[str, Any]:
    return _status()


@app.get("/dashboard/current.raw")
async def dashboard_raw(request: Request):
    etag = _photo_etag()
    if not etag or not RAW_PATH.exists():
        if etag and not RAW_PATH.exists():
            _clear_photo_mode()
        etag = _data_etag()
        if not RAW_PATH.exists() or _stored_data_etag() != etag:
            await render_once()
            etag = _data_etag()
    if request.headers.get("if-none-match", "").strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"'})
    return FileResponse(
        RAW_PATH,
        media_type="application/octet-stream",
        headers={"ETag": f'"{etag}"', "Cache-Control": "no-cache"},
    )


@app.get("/dashboard/check")
async def dashboard_check() -> dict[str, Any]:
    return {"etag": _etag()}


@app.post("/dashboard/trigger")
async def dashboard_trigger() -> dict[str, Any]:
    _clear_photo_mode()
    status = await render_once()
    return {"ok": True, **status}


@app.post("/dashboard/photo")
async def upload_photo(photo: UploadFile = File(...)) -> dict[str, Any]:
    contents = await photo.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty photo upload")

    try:
        black, yellow, rendered_etag = photo_renderer.render_photo(contents)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid or unsupported image") from exc

    saved_etag = photo_renderer.save_photo_frame(black, yellow)
    _write_photo_etag(saved_etag)
    return {
        "ok": True,
        "etag": saved_etag or rendered_etag,
        "size": f"{photo_renderer.WIDTH}x{photo_renderer.HEIGHT}",
    }


@app.post("/dashboard/ddl")
async def dashboard_ddl(body: DDLListBody) -> dict[str, Any]:
    items = [_dump_model(item) for item in body.items]
    storage.set_ddl_items(items)
    status = await render_once()
    return {"ok": True, "items": storage.get_ddl_items(), "etag": status["etag"]}


@app.get("/dashboard/ddl/list")
async def dashboard_ddl_list() -> dict[str, Any]:
    items = storage.get_ddl_items()
    # 动态重算 days_left：只要 item 有 due_str / date，就按今天日期重新计算，
    # 避免添加时写死后不再随日期变化。
    _recalc_days_left(items)
    return {"items": items}


@app.post("/dashboard/ddl/edit")
async def dashboard_ddl_edit(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    items = storage.get_ddl_items()
    action = str(data.get("action") or data.get("op") or "add").lower()
    index = data.get("index", data.get("id", -1))
    try:
        idx = int(index)
    except (TypeError, ValueError):
        idx = -1

    if action in {"delete", "remove", "del"}:
        ok = 0 <= idx < len(items)
        if ok:
            items.pop(idx)
    else:
        item = _normalize_ddl_item(_item_from_payload(data))
        if action in {"update", "edit"} and 0 <= idx < len(items):
            items[idx] = item
            ok = True
        elif action in {"add", "create"}:
            items.append(item)
            ok = True
        else:
            ok = False

    storage.set_ddl_items(items)
    etag = _data_etag()
    if not _photo_active():
        status = await render_once()
        etag = status["etag"]
    return {"ok": ok, "items": storage.get_ddl_items(), "etag": etag}


@app.post("/dashboard/plan/today")
async def dashboard_plan_today(body: PlanPushBody) -> dict[str, Any]:
    items = [_dump_model(item) for item in body.items]
    exams = [_dump_model(exam) for exam in body.exams]
    storage.set_plan(items, exams)
    etag = _data_etag()
    if not _photo_active():
        status = await render_once()
        etag = status["etag"]
    return {"ok": True, "plan": storage.get_plan(), "etag": etag}


@app.post("/dashboard/plan/tick")
async def dashboard_plan_tick(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    ok = storage.tick_plan_item(data.get("index", -1))
    etag = _data_etag()
    if ok and not _photo_active():
        status = await render_once()
        etag = status["etag"]
    return {"ok": ok, "plan": storage.get_plan(), "etag": etag}


@app.get("/dashboard/plan/list")
async def dashboard_plan_list() -> dict[str, Any]:
    plan = storage.get_plan()
    # 考试的 days_left 按今天日期动态刷新，前端列表和墨水屏都看到准确天数
    _recalc_days_left(plan.get("exams", []))
    return plan


@app.post("/dashboard/plan/edit")
async def dashboard_plan_edit(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    action = str(data.get("action", "add")).lower()
    index = data.get("index", -1)
    item = data.get("item", {})

    if action in {"delete", "remove", "del"}:
        ok = storage.delete_plan_item(index)
    elif action in {"update", "edit"}:
        ok = storage.update_plan_item(index, item)
    else:
        ok = storage.add_plan_item(item)

    etag = _data_etag()
    if not _photo_active():
        status = await render_once()
        etag = status["etag"]
    return {"ok": ok, "plan": storage.get_plan(), "etag": etag}


@app.post("/dashboard/exam/edit")
async def dashboard_exam_edit(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    action = str(data.get("action", "add")).lower()
    index = data.get("index", -1)
    item = data.get("item", {})

    if action in {"delete", "remove", "del"}:
        ok = storage.delete_exam_item(index)
    elif action in {"update", "edit"}:
        ok = storage.update_exam_item(index, item)
    else:
        if item.get("date") and not item.get("days_left"):
            item["days_left"] = _days_from_date(item["date"]) or 0
        ok = storage.add_exam_item(item)

    etag = _data_etag()
    if not _photo_active():
        status = await render_once()
        etag = status["etag"]
    return {"ok": ok, "plan": storage.get_plan(), "etag": etag}


@app.post("/dashboard/recite")
async def dashboard_recite(request: Request) -> dict[str, Any]:
    data = await _payload(request)
    storage.set_recite_text(renderer.format_recite_text(str(data.get("text", ""))))
    etag = _data_etag()
    if not _photo_active():
        status = await render_once()
        etag = status["etag"]
    text = storage.get_recite_text()
    return {"ok": True, "text": text, "active": bool(text.strip()), "etag": etag}


@app.post("/dashboard/recite/clear")
async def dashboard_recite_clear() -> dict[str, Any]:
    storage.clear_recite_text()
    etag = _data_etag()
    if not _photo_active():
        status = await render_once()
        etag = status["etag"]
    return {"ok": True, "text": "", "active": False, "etag": etag}


@app.get("/dashboard/recite/status")
async def dashboard_recite_status() -> dict[str, Any]:
    text = storage.get_recite_text()
    return {"text": text, "active": bool(text.strip())}


@app.get("/dashboard/health")
async def dashboard_health() -> dict[str, Any]:
    return {"ok": True, "time": datetime.now().isoformat(timespec="seconds")}


@app.get("/dashboard/download/firmware")
async def dashboard_download_firmware():
    for path in FIRMWARE_CANDIDATES:
        if path.exists():
            return FileResponse(path, filename="firmware.bin", media_type="application/octet-stream")
    return JSONResponse({"ok": False, "error": "firmware not found"}, status_code=404)


@app.get("/epaper.html")
async def epaper_dashboard():
    """Serve the HTML/CSS e-ink dashboard frontend."""
    html_path = BASE_DIR.parent / "epaper-dashboard" / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>epaper-dashboard not found</h1>", status_code=404)


@app.get("/epaper/styles.css")
async def epaper_styles():
    css_path = BASE_DIR.parent / "epaper-dashboard" / "styles.css"
    if css_path.exists():
        return Response(css_path.read_text(encoding="utf-8"), media_type="text/css")
    return Response("", status_code=404)


@app.get("/epaper/script.js")
async def epaper_script():
    js_path = BASE_DIR.parent / "epaper-dashboard" / "script.js"
    if js_path.exists():
        return Response(js_path.read_text(encoding="utf-8"), media_type="application/javascript")
    return Response("", status_code=404)


@app.get("/favicon.ico")
async def favicon():
    return Response("", media_type="image/x-icon")

@app.get("/", response_class=HTMLResponse)
async def control_panel(request: Request):
    status = _status()
    raw = RAW_PATH.read_bytes() if RAW_PATH.exists() else b""
    return templates.TemplateResponse(
        "control.html",
        {
            "request": request,
            "status": status,
            "ddl_items": storage.get_ddl_items(),
            "plan": storage.get_plan(),
            "recite_text": storage.get_recite_text(),
            "raw_size": len(raw),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cron", action="store_true", help="render once and exit")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8646)
    args = parser.parse_args()
    if args.cron:
        asyncio.run(render_once())
        return

    import uvicorn

    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
