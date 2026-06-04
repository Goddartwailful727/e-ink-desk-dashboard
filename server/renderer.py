from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    from .storage import DATA_DIR
except ImportError:
    from storage import DATA_DIR


WIDTH = 800
HEIGHT = 480
FRAME_BYTES = WIDTH * HEIGHT // 8
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

_WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
_RECITE_HEADING_PREFIXES = (
    "一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、", "十、",
    "1.", "2.", "3.", "4.", "5.",
)
_RECITE_BREAK_CHARS = set(" \t,.;:!?，。；：、！？)]}）】》")

_FOCUS_MAP = {}


def _load_fonts() -> dict[str, ImageFont.ImageFont]:
    try:
        return {
            "title": ImageFont.truetype(FONT_BOLD, 20),
            "large": ImageFont.truetype(FONT_BOLD, 20),
            "medium": ImageFont.truetype(FONT_BOLD, 18),
            "small": ImageFont.truetype(FONT_REGULAR, 15),
            "tiny": ImageFont.truetype(FONT_REGULAR, 13),
        }
    except OSError:
        f = ImageFont.load_default()
        return {k: f for k in ["title", "large", "medium", "small", "tiny"]}


def _tw(d, text, font) -> int:
    try:
        return int(d.textlength(text, font=font))
    except Exception:
        bbox = d.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]


def _truncate_px(d, text, font, max_px) -> str:
    """Truncate text to fit max_px width."""
    if _tw(d, text, font) <= max_px:
        return text
    text = text.rstrip()
    if text.endswith("..."):
        text = text[:-3].rstrip()
    while text and _tw(d, text + "...", font) > max_px:
        text = text[:-1].rstrip()
    return text + "..." if text else "..."


def _append_ellipsis_px(d, text, font, max_px) -> str:
    text = text.rstrip()
    while text and _tw(d, text + "...", font) > max_px:
        text = text[:-1].rstrip()
    return f"{text}..." if text else "..."


def _is_recite_heading(line: str) -> bool:
    return line.startswith(_RECITE_HEADING_PREFIXES)


def _split_recite_paragraphs(raw_text: str) -> list[str]:
    text = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    return [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]


def _wrap_recite_line(d, line: str, font, max_width: int) -> list[str]:
    line = re.sub(r"[ \t]+", " ", line.strip())
    if not line:
        return []

    wrapped: list[str] = []
    remaining = line
    while remaining:
        if _tw(d, remaining, font) <= max_width:
            wrapped.append(remaining)
            break

        lo, hi = 1, len(remaining)
        best = 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if _tw(d, remaining[:mid], font) <= max_width:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        split_at = best
        min_break = max(1, int(best * 0.55))
        for i in range(best - 1, min_break - 1, -1):
            ch = remaining[i]
            if ch.isspace():
                split_at = i
                break
            if ch in _RECITE_BREAK_CHARS:
                split_at = i + 1
                break

        candidate = remaining[:split_at].strip()
        if not candidate:
            split_at = best
            candidate = remaining[:split_at].strip()
        if not candidate:
            break

        wrapped.append(candidate)
        remaining = remaining[split_at:].lstrip()

    return wrapped


def _fit_recite_text(raw_text: str, font, max_width: int = 760, max_lines: int = 19) -> list[str]:
    """Wrap recite text to fit the 800x480 display."""
    if max_lines <= 0:
        return []

    img = Image.new("1", (WIDTH, HEIGHT), 1)
    d = ImageDraw.Draw(img)
    paragraphs = _split_recite_paragraphs(raw_text)
    lines: list[str] = []
    truncated = False

    for para_index, para in enumerate(paragraphs):
        para_lines: list[str] = []
        for raw_line in para.split("\n"):
            para_lines.extend(_wrap_recite_line(d, raw_line, font, max_width))
        if not para_lines:
            continue

        if para_index > 0 and lines:
            if len(lines) >= max_lines - 1:
                truncated = True
                break
            lines.append("")

        for line in para_lines:
            if len(lines) >= max_lines:
                truncated = True
                break
            lines.append(line)
        if truncated:
            break

    if truncated:
        while lines and not lines[-1]:
            lines.pop()
        if lines:
            lines[-1] = _append_ellipsis_px(d, lines[-1], font, max_width)
        else:
            lines = ["..."]

    return lines


def format_recite_text(raw_text: str) -> str:
    """Format submitted recite text for the 800x480 recite display."""
    if not str(raw_text or "").strip():
        return ""
    fonts = _load_fonts()
    return "\n".join(_fit_recite_text(raw_text, fonts["small"], max_width=700, max_lines=19))


def _plan_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    plan = data.get("plan", [])
    if isinstance(plan, dict):
        items = plan.get("items", [])
    else:
        items = plan
    return items if isinstance(items, list) else []


def render(data: dict[str, Any]) -> tuple[bytes, bytes, str]:
    """Render 800x480 pure black-white dashboard. Returns (black_bytes, yellow_bytes, etag)."""
    fonts = _load_fonts()
    img = Image.new("1", (WIDTH, HEIGHT), 1)
    d = ImageDraw.Draw(img)

    # Check recite mode
    recite_text = str(data.get("recite") or "").strip()
    if recite_text:
        return _render_recite(d, fonts, data, recite_text)

    now_str = data.get("now")
    if isinstance(now_str, str):
        now = datetime.fromisoformat(now_str)
    else:
        now = datetime.now()

    M = 14

    # ── HEADER ──
    hh = 36
    d.rectangle([(M, 4), (WIDTH - M, 4 + hh)], fill=0)
    date_text = f"{now.month}月{now.day}日 周{_WEEKDAYS[now.weekday()]}"
    d.text((M + 14, 9), date_text, fill=1, font=fonts["title"])

    # Weather
    weather = data.get("weather")
    if weather:
        cur = weather.get("current", {})
        temp = cur.get("temp") or "--"
        temp_w = _tw(d, f"{temp}°", fonts["medium"])
        d.text((WIDTH - M - 14 - temp_w, 10), f"{temp}°", fill=1, font=fonts["medium"])
        fc = weather.get("forecast", [])
        fcx = WIDTH - M - 130
        for i, f_item in enumerate(fc[:2]):
            fmax = f_item.get("temp_max", "--")
            fmin = f_item.get("temp_min", "--")
            label = ["明天", "后天"][i]
            d.text((fcx, 6 + i * 13), f"{label} {fmax}/{fmin}", fill=1, font=fonts["tiny"])
            fcx += 70

    # ── TWO-COLUMN ──
    cy = 4 + hh + 4
    ch = HEIGHT - cy - 4 - 32
    col_gap = 10
    col_lw = 520
    col_rw = WIDTH - M * 2 - col_gap - col_lw

    # ── LEFT: PLAN ──
    lx, ly = M, cy
    d.rectangle([(lx, ly), (lx + col_lw, ly + ch)], outline=0, width=3)
    d.rectangle([(lx + 1, ly + 1), (lx + col_lw - 1, ly + 26)], fill=0)
    d.text((lx + 14, ly + 1), "今日计划", fill=1, font=fonts["title"])

    plan_items = _plan_items(data)
    study_items = [p for p in plan_items if not p.get("break")]
    total = len(study_items)
    done = len([p for p in study_items if p.get("done")])
    d.text((lx + col_lw - 14 - _tw(d, f"{done}/{total}", fonts["medium"]), ly + 2),
           f"{done}/{total}", fill=1, font=fonts["medium"])

    # Schedule items
    sy = ly + 28
    item_h = 28
    reserved = 20
    max_items_y = ly + ch - reserved
    max_items = max(1, min(len(plan_items), (max_items_y - sy) // item_h))

    for i, item in enumerate(plan_items[:max_items]):
        y = sy + i * item_h
        if y + item_h > max_items_y:
            break
        time_block = str(item.get("time", ""))
        task = str(item.get("task", ""))
        done_flag = item.get("done", False)
        is_break = item.get("break", False)

        d.text((lx + 10, y), time_block, fill=0, font=fonts["small"])
        tw_t = _tw(d, time_block, fonts["small"])

        cb = lx + 10 + tw_t + 6
        if is_break:
            d.ellipse([(cb + 2, y + 6), (cb + 12, y + 16)], fill=0)
            tx = cb + 16
        else:
            if done_flag:
                d.rectangle([(cb, y + 4), (cb + 12, y + 16)], outline=0, width=1)
            else:
                d.rectangle([(cb, y + 4), (cb + 12, y + 16)], outline=0, width=2)
            tx = cb + 16

        mxw = lx + col_lw - tx - 10
        dt = _truncate_px(d, task, fonts["small"], mxw)
        d.text((tx, y), dt, fill=0, font=fonts["small"])

        if done_flag and not is_break:
            mid_y = y + 10
            dt_w = min(_tw(d, dt, fonts["small"]), mxw)
            d.line([(tx, mid_y), (tx + dt_w, mid_y)], fill=0, width=2)

    # Progress bar
    pbar_y = sy + max_items * item_h + 8
    if total > 0:
        pct = done / total
        pw = col_lw - 20
        d.rectangle([(lx + 10, pbar_y), (lx + 10 + pw, pbar_y + 6)], outline=0, width=2)
        if pct > 0:
            fw = max(1, int(pw * pct))
            d.rectangle([(lx + 11, pbar_y + 1), (lx + 10 + fw, pbar_y + 5)], fill=0)
        pct_text = f"{int(pct * 100)}%"
        d.text((lx + col_lw - 14 - _tw(d, pct_text, fonts["medium"]), pbar_y - 18),
               pct_text, fill=0, font=fonts["medium"])

    # ── RIGHT: EXAM COUNTDOWN ──
    rx = lx + col_lw + col_gap
    ry = cy
    d.rectangle([(rx, ry), (rx + col_rw, ry + ch)], outline=0, width=3)
    d.rectangle([(rx + 1, ry + 1), (rx + col_rw - 1, ry + 26)], fill=0)
    d.text((rx + 12, ry + 1), "倒计时", fill=1, font=fonts["title"])

    exams = data.get("exams", [])
    ey = ry + 32
    eh = 40

    for i, exam in enumerate(exams[:8]):
        y = ey + i * eh
        if y + eh > ry + ch - 4:
            break
        name = str(exam.get("name", ""))
        days = exam.get("days_left", 0)
        if days <= 7:
            fd = fonts["medium"]
        elif days <= 15:
            fd = fonts["small"]
        else:
            fd = fonts["tiny"]
        d.text((rx + 12, y), name, fill=0, font=fonts["tiny"])
        days_text = f"{days}天"
        d.text((rx + 12, y + 14), days_text, fill=0, font=fd)
        if i < len(exams) - 1:
            d.line([(rx + 10, y + eh - 2), (rx + col_rw - 10, y + eh - 2)], fill=0, width=1)

    # ── FOOTER ──
    fy = HEIGHT - 32
    fw = WIDTH - 2 * M

    d.line([(M, fy), (M + fw, fy)], fill=0, width=1)
    d.line([(M, fy + 2), (M + fw, fy + 2)], fill=0, width=3)

    today = now.strftime("%m-%d")
    focus = "刑诉+行政法+国社下"
    for dk in sorted(_FOCUS_MAP.keys(), reverse=True):
        if today >= dk:
            focus = _FOCUS_MAP.get(dk, focus)
            break

    d.text((M + 6, fy + 6), ">", fill=0, font=fonts["tiny"])
    d.text((M + 20, fy + 6), focus, fill=0, font=fonts["medium"])

    ut = "已更新"
    d.text((M + fw - _tw(d, ut, fonts["tiny"]), fy + 5), ut, fill=0, font=fonts["tiny"])

    # ── OUTPUT ──
    black_bytes = img.tobytes("raw", "1")
    yellow_bytes = Image.new("1", (WIDTH, HEIGHT), 1).tobytes("raw", "1")
    etag = hashlib.md5(black_bytes + yellow_bytes).hexdigest()
    return black_bytes, yellow_bytes, etag


def _render_recite(d, fonts, data, recite_text) -> tuple[bytes, bytes, str]:
    """Full-screen recite mode."""
    from datetime import datetime
    W, H = WIDTH, HEIGHT
    img = Image.new("1", (W, H), 1)
    d = ImageDraw.Draw(img)

    M = 12
    now_str = data.get("now")
    if isinstance(now_str, str):
        now = datetime.fromisoformat(now_str)
    else:
        now = datetime.now()

    # Header
    d.rectangle([(M, 4), (W - M, 4 + 30)], fill=0)
    d.text((M + 12, 6), "背诵", fill=1, font=fonts["title"])
    d.text((W - M - 12 - _tw(d, f"{now.month}/{now.day}", fonts["tiny"]), 8),
           f"{now.month}/{now.day}", fill=1, font=fonts["tiny"])

    # Content
    cy = 4 + 30 + 6
    ch = H - cy - 4
    max_y = cy + ch

    y = cy + 2
    line_h = 22
    body_x = M + 12
    body_width = min(760, W - body_x - M)
    max_lines = max(1, (max_y - y) // line_h)
    lines = _fit_recite_text(recite_text, fonts["small"], max_width=body_width, max_lines=max_lines)

    for line in lines:
        if y + line_h > max_y:
            break
        line = line.strip()
        if not line:
            y += 6
            continue

        if _is_recite_heading(line):
            x = M + 10
            font = fonts["medium"]
        elif line.startswith("（"):
            x = M + 18
            font = fonts["small"]
        else:
            x = body_x
            font = fonts["small"]

        max_width = W - x - M
        d.text((x, y), _truncate_px(d, line, font, max_width), fill=0, font=font)
        y += line_h

    black_bytes = img.tobytes("raw", "1")
    yellow_bytes = Image.new("1", (W, H), 1).tobytes("raw", "1")
    etag = hashlib.md5(black_bytes + yellow_bytes).hexdigest()
    return black_bytes, yellow_bytes, etag


def save_frame(black_bytes, yellow_bytes):
    """Write bitmap to data/current.raw and update etag."""
    data_dir = DATA_DIR
    raw_path = data_dir / "current.raw"
    raw_path.write_bytes(black_bytes + yellow_bytes)
    etag = hashlib.md5(black_bytes + yellow_bytes).hexdigest()
    etag_path = data_dir / "etag.txt"
    etag_path.write_text(etag)
    return etag
