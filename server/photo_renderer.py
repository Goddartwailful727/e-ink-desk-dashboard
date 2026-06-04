from __future__ import annotations

import hashlib
import io

from PIL import Image, ImageOps

try:
    from .storage import DATA_DIR
except ImportError:
    from storage import DATA_DIR


WIDTH = 800
HEIGHT = 480
FRAME_BYTES = WIDTH * HEIGHT // 8


def _resample_filter():
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return Image.LANCZOS


def render_photo(image_bytes: bytes) -> tuple[bytes, bytes, str]:
    """Convert an uploaded photo to an 800x480 1-bit e-ink bitmap."""
    with Image.open(io.BytesIO(image_bytes)) as opened:
        img = ImageOps.exif_transpose(opened)
        if img.mode != "RGB":
            img = img.convert("RGB")
        else:
            img = img.copy()

    target_ratio = WIDTH / HEIGHT
    image_ratio = img.width / img.height
    if image_ratio > target_ratio:
        crop_width = int(img.height * target_ratio)
        left = (img.width - crop_width) // 2
        img = img.crop((left, 0, left + crop_width, img.height))
    elif image_ratio < target_ratio:
        crop_height = int(img.width / target_ratio)
        top = (img.height - crop_height) // 2
        img = img.crop((0, top, img.width, top + crop_height))

    canvas = img.resize((WIDTH, HEIGHT), _resample_filter())

    gray = canvas.convert("L")
    pixels = gray.load()

    for y in range(HEIGHT):
        for x in range(WIDTH):
            old = pixels[x, y]
            new = 0 if old < 128 else 255
            pixels[x, y] = new
            err = old - new

            if x + 1 < WIDTH:
                pixels[x + 1, y] = max(0, min(255, pixels[x + 1, y] + err * 7 // 16))
            if y + 1 < HEIGHT:
                if x > 0:
                    pixels[x - 1, y + 1] = max(0, min(255, pixels[x - 1, y + 1] + err * 3 // 16))
                pixels[x, y + 1] = max(0, min(255, pixels[x, y + 1] + err * 5 // 16))
                if x + 1 < WIDTH:
                    pixels[x + 1, y + 1] = max(0, min(255, pixels[x + 1, y + 1] + err // 16))

    black = bytearray(FRAME_BYTES)
    for y in range(HEIGHT):
        row_offset = y * (WIDTH // 8)
        for x in range(WIDTH):
            if pixels[x, y] >= 128:
                byte_idx = row_offset + (x // 8)
                bit_idx = 7 - (x % 8)
                black[byte_idx] |= 1 << bit_idx

    yellow = bytes([0xFF]) * FRAME_BYTES
    etag = hashlib.md5(bytes(black) + yellow).hexdigest()
    return bytes(black), yellow, etag


def save_photo_frame(black_bytes: bytes, yellow_bytes: bytes) -> str:
    """Save the photo frame as the current raw e-ink frame."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame = black_bytes + yellow_bytes
    (DATA_DIR / "current.raw").write_bytes(frame)
    etag = hashlib.md5(frame).hexdigest()
    (DATA_DIR / "etag.txt").write_text(etag, encoding="utf-8")
    return etag
