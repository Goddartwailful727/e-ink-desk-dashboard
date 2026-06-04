from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from .renderer import FRAME_BYTES, HEIGHT, MEDIUM, TITLE, WIDTH, _font, _pack_black_plane
    from .storage import DATA_DIR
except ImportError:
    from renderer import FRAME_BYTES, HEIGHT, MEDIUM, TITLE, WIDTH, _font, _pack_black_plane
    from storage import DATA_DIR


BODY = _font("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 18)


def render(text: str) -> tuple[bytes, bytes, str]:
    img = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, WIDTH, 42), fill=0)
    draw.text((24, 10), "背诵", font=TITLE, fill=1)

    y = 66
    max_y = HEIGHT - 24
    paragraphs = [p.strip() for p in str(text or "").splitlines() if p.strip()]
    for paragraph in paragraphs:
        for line in textwrap.wrap(paragraph, width=34):
            if y > max_y:
                draw.text((724, HEIGHT - 28), "...", font=MEDIUM, fill=0)
                black = _pack_black_plane(img)
                yellow = bytes([0xFF]) * FRAME_BYTES
                return black, yellow, hashlib.sha1(black + yellow).hexdigest()[:16]
            draw.text((42, y), line, font=BODY, fill=0)
            y += 29
        y += 14

    black = _pack_black_plane(img)
    yellow = bytes([0xFF]) * FRAME_BYTES
    return black, yellow, hashlib.sha1(black + yellow).hexdigest()[:16]


def save_frame(black: bytes, yellow: bytes) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = DATA_DIR / "current.raw"
    etag = hashlib.sha1(black + yellow).hexdigest()[:16]
    raw_path.write_bytes(black + yellow)
    (DATA_DIR / "etag.txt").write_text(etag, encoding="utf-8")
