"""공통 디자인 요소: 색상, 폰트, 이미지/텍스트 유틸."""
import hashlib
import io
from functools import lru_cache

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import CACHE_DIR, FONT_DIR

ORANGE = (253, 122, 49)
ORANGE_DARK = (226, 92, 20)
CREAM = (255, 246, 239)
DARK = (28, 28, 32)
GREY = (138, 138, 146)
LIGHT_GREY = (232, 232, 236)
WHITE = (255, 255, 255)

_FONT_URL = ("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/packages/"
             "pretendard/dist/public/static/alternative/Pretendard-{w}.ttf")
WEIGHTS = ["Medium", "SemiBold", "Bold", "ExtraBold", "Black"]


def ensure_fonts() -> None:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for w in WEIGHTS:
        p = FONT_DIR / f"Pretendard-{w}.ttf"
        if not p.exists():
            r = requests.get(_FONT_URL.format(w=w), timeout=60)
            r.raise_for_status()
            p.write_bytes(r.content)


@lru_cache(maxsize=None)
def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"Pretendard-{weight}.ttf"), size)


def won(n: int) -> str:
    return f"{int(n):,}원"


def discount_pct(o: dict) -> int:
    bps = o.get("discountRateBps") or 0
    if not bps and o.get("listPrice"):
        bps = round((1 - o["unitPrice"] / o["listPrice"]) * 10000)
    return round(bps / 100)


def season_label(o: dict) -> str:
    return {"all_season": "사계절", "summer": "여름용", "winter": "겨울용"}.get(o.get("season") or "", "")


def spec_line(o: dict) -> str:
    s = o.get("size") or ""
    li, sr = o.get("loadIndex"), o.get("speedRating")
    if li and sr and sr != "-":
        s += f" {li}{sr}"
    return s


def clean_title(o: dict) -> str:
    brand, pattern = (o.get("brand") or "").strip(), (o.get("pattern") or "").strip()
    if pattern:
        return f"{brand} {pattern}".strip()
    return " ".join((o.get("title") or "").split())


def fetch_image(url: str) -> Image.Image:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / (hashlib.md5(url.encode()).hexdigest() + ".img")
    if not p.exists():
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        p.write_bytes(r.content)
    return Image.open(io.BytesIO(p.read_bytes())).convert("RGBA")


def trim(img: Image.Image, pad: int = 8) -> Image.Image:
    """투명/흰 여백을 잘라 상품을 꽉 차게 만든다."""
    rgb = img.convert("RGB")
    bg = Image.new("RGB", img.size, (255, 255, 255))
    from PIL import ImageChops
    diff = ImageChops.difference(rgb, bg).convert("L").point(lambda v: 255 if v > 18 else 0)
    alpha = img.getchannel("A").point(lambda v: 255 if v > 18 else 0)
    mask = ImageChops.multiply(diff, alpha)
    box = mask.getbbox()
    if not box:
        return img
    l, t, r, b = box
    return img.crop((max(0, l - pad), max(0, t - pad), min(img.width, r + pad), min(img.height, b + pad)))


def fit_into(img: Image.Image, w: int, h: int) -> Image.Image:
    s = min(w / img.width, h / img.height)
    return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)


def text_w(f: ImageFont.FreeTypeFont, text: str) -> int:
    return int(f.getlength(text))


def fit_font(text: str, weight: str, max_size: int, max_width: int, min_size: int = 24):
    size = max_size
    while size > min_size and text_w(font(weight, size), text) > max_width:
        size -= 2
    return font(weight, size)


def wrap(text: str, f: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 2) -> list[str]:
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_w(f, trial) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while text_w(f, lines[-1] + "…") > max_width and lines[-1]:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines


def shadowed_card(canvas: Image.Image, box, radius: int, fill=WHITE, blur: int = 28, offset: int = 14, alpha: int = 55):
    l, t, r, b = box
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((l, t + offset, r, b + offset), radius, fill=(80, 40, 10, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh)
    ImageDraw.Draw(canvas).rounded_rectangle(box, radius, fill=fill)


def pill(draw: ImageDraw.ImageDraw, xy, text: str, f, fg, bg, pad_x: int = 22, pad_y: int = 10, outline=None) -> int:
    x, y = xy
    w = text_w(f, text)
    asc, desc = f.getmetrics()
    h = asc + desc
    draw.rounded_rectangle((x, y, x + w + pad_x * 2, y + h + pad_y * 2), (h + pad_y * 2) // 2,
                           fill=bg, outline=outline, width=3 if outline else 0)
    draw.text((x + pad_x, y + pad_y), text, font=f, fill=fg)
    return x + w + pad_x * 2


def strike_text(draw, xy, text: str, f, fill):
    x, y = xy
    draw.text((x, y), text, font=f, fill=fill)
    l, t, r, b = draw.textbbox((x, y), text, font=f)
    mid = (t + b) // 2
    draw.line((l - 4, mid, r + 4, mid), fill=fill, width=max(2, f.size // 14))
    return r


def discount_badge(diameter: int, pct: int) -> Image.Image:
    im = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, diameter - 1, diameter - 1), fill=ORANGE)
    d.ellipse((8, 8, diameter - 9, diameter - 9), outline=WHITE, width=3)
    big = font("Black", int(diameter * 0.34))
    small = font("Bold", int(diameter * 0.15))
    t1, t2 = f"{pct}%", "할인"
    total_h = big.size + small.size + 4
    y0 = (diameter - total_h) // 2 - int(diameter * 0.03)
    d.text(((diameter - text_w(big, t1)) // 2, y0), t1, font=big, fill=WHITE)
    d.text(((diameter - text_w(small, t2)) // 2, y0 + big.size + 6), t2, font=small, fill=WHITE)
    return im
