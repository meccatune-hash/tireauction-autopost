"""릴스/쇼츠용 1080x1920 (9:16) 세로 홍보 영상.

구성: 인트로(2.5s) → 상품 N개(각 3.5s) → 아웃트로(3s), 30fps.
프레임은 Pillow 로 그리고 imageio-ffmpeg 에 포함된 ffmpeg 로 H.264 인코딩합니다.
assets/bgm.mp3 가 있으면 배경음악으로 사용하고, 없으면 무음 오디오 트랙을 넣습니다.
"""
import math
import subprocess
from datetime import date
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

from config import ASSETS_DIR, BRAND_NAME, SITE_URL, SUB_TAGLINE, TAGLINE
from src import design as D
from src.scrape import image_url

W, H, FPS = 1080, 1920, 30
INTRO, ITEM, OUTRO, XFADE = 2.5, 3.5, 3.0, 0.25
# 인스타/유튜브 UI 가 덮는 영역(하단·우측)을 피해 핵심 정보는 y 200~1500 안에 배치


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_back(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _layer(size) -> Image.Image:
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _fade(img: Image.Image, a: float) -> Image.Image:
    if a >= 1:
        return img
    out = img.copy()
    out.putalpha(out.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return out


def _paste(canvas, layer, xy, alpha=1.0):
    if alpha <= 0:
        return
    canvas.alpha_composite(_fade(layer, alpha), (int(xy[0]), int(xy[1])))


def _text_layer(lines, weight, size, color, align="left", spacing=1.18, width=None):
    f = D.font(weight, size)
    lw = max(D.text_w(f, s) for s in lines)
    width = width or lw + 10
    lh = int(size * spacing)
    im = _layer((width, lh * len(lines) + int(size * 0.3)))
    d = ImageDraw.Draw(im)
    for i, s in enumerate(lines):
        x = 0 if align == "left" else (width - D.text_w(f, s)) // 2
        d.text((x, i * lh), s, font=f, fill=color)
    return im


# ── 인트로 ───────────────────────────────────────────────
class Intro:
    dur = INTRO

    def __init__(self, today: date, headline: str, count: int, max_pct: int):
        self.bg = Image.new("RGBA", (W, H), D.ORANGE + (255,))
        d = ImageDraw.Draw(self.bg)
        for i in range(-H, W, 120):  # 은은한 사선 패턴
            d.line((i, 0, i + H, H), fill=(255, 138, 70), width=40)
        self.brand = _text_layer([BRAND_NAME], "Black", 72, D.WHITE, align="center", width=W)
        self.date = _layer((W, 90))
        df = D.font("Bold", 40)
        ds = f"{today.month}월 {today.day}일"
        dw = D.text_w(df, ds) + 60
        D.pill(ImageDraw.Draw(self.date), ((W - dw) // 2, 0), ds, df, D.ORANGE, D.WHITE, pad_x=30, pad_y=14)
        self.title = _text_layer(headline.split("\n"), "Black", 132, D.WHITE, align="center", width=W)
        self.sub = _text_layer([f"TOP {count}  ·  최대 {max_pct}% 할인"], "ExtraBold", 60, (255, 236, 222),
                               align="center", width=W)

    def frame(self, t):
        im = self.bg.copy()
        _paste(im, self.brand, (0, 300), ease_out(t / 0.4))
        _paste(im, self.date, (0, 560 + 40 * (1 - ease_out(t / 0.5))), ease_out(t / 0.5))
        k = ease_out((t - 0.15) / 0.6)
        _paste(im, self.title, (0, 700 + 120 * (1 - k)), k)
        k2 = ease_out((t - 0.6) / 0.5)
        _paste(im, self.sub, (0, 1080 + 60 * (1 - k2)), k2)
        return im


# ── 상품 ───────────────────────────────────────────────
class Item:
    dur = ITEM
    CARD = (70, 300, W - 70, 1080)

    def __init__(self, o: dict, rank: int):
        self.o = o
        self.bg = Image.new("RGBA", (W, H), D.CREAM + (255,))
        d = ImageDraw.Draw(self.bg)
        d.rectangle((0, 0, W, 210), fill=D.ORANGE)
        d.text((70, 92), BRAND_NAME, font=D.font("Black", 60), fill=D.WHITE)
        rf = D.font("Black", 44)
        rs = f"TOP {rank}"
        D.pill(d, (W - 70 - D.text_w(rf, rs) - 56, 92), rs, rf, D.ORANGE, D.WHITE, pad_x=28, pad_y=10)
        D.shadowed_card(self.bg, self.CARD, 48)
        self.prod = D.fit_into(D.trim(D.fetch_image(image_url(o))), 820, 660)

        pct = D.discount_pct(o)
        self.badge = D.discount_badge(240, pct) if pct >= 5 else None

        # 정보 블록
        info = _layer((W - 140, 420))
        di = ImageDraw.Draw(info)
        chip = D.font("Bold", 34)
        x = D.pill(di, (0, 0), o.get("brand") or "", chip, D.WHITE, D.DARK, pad_x=22, pad_y=8) + 14
        if D.season_label(o):
            D.pill(di, (x, 0), D.season_label(o), chip, D.ORANGE_DARK, D.CREAM, pad_x=22, pad_y=8, outline=D.ORANGE)
        title = D.clean_title(o)
        tf = D.fit_font(title, "ExtraBold", 72, W - 140, 44)
        di.text((0, 78), title, font=tf, fill=D.DARK)
        di.text((2, 168), D.spec_line(o), font=D.font("SemiBold", 42), fill=D.GREY)
        y = 240
        if o.get("listPrice") and o["listPrice"] > o["unitPrice"]:
            D.strike_text(di, (2, y + 34), D.won(o["listPrice"]), D.font("Medium", 44), D.GREY)
            px = D.text_w(D.font("Medium", 44), D.won(o["listPrice"])) + 34
        else:
            px = 0
        pf = D.font("Black", 100)
        di.text((px, y), D.won(o["unitPrice"]), font=pf, fill=D.ORANGE)
        di.text((px + D.text_w(pf, D.won(o["unitPrice"])) + 14, y + 52), "/ 1본", font=D.font("SemiBold", 36),
                fill=D.GREY)
        self.info = info

        perks = []
        if (o.get("deliveryFee") or 0) == 0:
            perks.append("무료배송")
        if o.get("installFee"):
            perks.append(f"장착비 {D.won(o['installFee'])}")
        self.perks = _text_layer(["  ·  ".join(perks) or " "], "Bold", 36, D.ORANGE_DARK)

    def frame(self, t):
        im = self.bg.copy()
        l, tp, r, b = self.CARD
        z = (0.94 + 0.10 * (t / self.dur)) * (0.9 + 0.1 * ease_out(t / 0.4))
        p = self.prod.resize((int(self.prod.width * z), int(self.prod.height * z)), Image.BILINEAR)
        _paste(im, p, ((l + r - p.width) / 2, (tp + b - p.height) / 2), ease_out(t / 0.3))
        if self.badge is not None:
            k = ease_back((t - 0.35) / 0.4)
            if k > 0.01:
                s = max(1, int(240 * k))
                bd = self.badge.resize((s, s), Image.BILINEAR)
                cx, cy = W - 70 - 110, 290
                _paste(im, bd, (cx - s / 2, cy - s / 2))
        k = ease_out((t - 0.2) / 0.5)
        _paste(im, self.info, (70, 1130 + 80 * (1 - k)), k)
        k2 = ease_out((t - 0.7) / 0.4)
        _paste(im, self.perks, (72, 1560 + 30 * (1 - k2)), k2)
        return im


# ── 아웃트로 ───────────────────────────────────────────
class Outro:
    dur = OUTRO

    def __init__(self):
        self.bg = Image.new("RGBA", (W, H), D.DARK + (255,))
        d = ImageDraw.Draw(self.bg)
        d.rectangle((0, 0, W, 16), fill=D.ORANGE)
        self.l1 = _text_layer([TAGLINE.split("! ")[0] + "!"], "Black", 110, D.ORANGE, align="center", width=W)
        self.l2 = _text_layer([TAGLINE.split("! ")[1]], "ExtraBold", 72, D.WHITE, align="center", width=W)
        self.l3 = _text_layer([SUB_TAGLINE], "SemiBold", 46, (200, 200, 206), align="center", width=W)
        box = _layer((W, 300))
        db = ImageDraw.Draw(box)
        db.rounded_rectangle((110, 0, W - 110, 280), 40, fill=D.ORANGE)
        f1, f2 = D.font("ExtraBold", 52), D.font("Bold", 40)
        s1 = f"앱에서 '{BRAND_NAME}' 검색"
        s2 = SITE_URL.replace("https://", "")
        db.text(((W - D.text_w(f1, s1)) // 2, 60), s1, font=f1, fill=D.WHITE)
        db.text(((W - D.text_w(f2, s2)) // 2, 160), s2, font=f2, fill=(255, 232, 216))
        self.cta = box
        self.stores = _text_layer(["App Store  ·  Google Play"], "Bold", 40, (170, 170, 178), align="center", width=W)

    def frame(self, t):
        im = self.bg.copy()
        k = ease_out(t / 0.5)
        _paste(im, self.l1, (0, 420 + 60 * (1 - k)), k)
        k = ease_out((t - 0.2) / 0.5)
        _paste(im, self.l2, (0, 570 + 60 * (1 - k)), k)
        k = ease_out((t - 0.4) / 0.5)
        _paste(im, self.l3, (0, 720), k)
        k = ease_back((t - 0.7) / 0.5)
        if k > 0.01:
            s = max(0.01, k)
            c = self.cta.resize((int(W * s), int(300 * s)), Image.BILINEAR)
            _paste(im, c, ((W - c.width) / 2, 920 + (300 - c.height) / 2))
        _paste(im, self.stores, (0, 1290), ease_out((t - 1.0) / 0.5))
        return im


def render_video(offers: list[dict], today: date, out_path: Path, headline: str = "오늘의\n타이어 특가") -> Path:
    max_pct = max(D.discount_pct(o) for o in offers)
    scenes = [Intro(today, headline, len(offers), max_pct)]
    scenes += [Item(o, i + 1) for i, o in enumerate(offers)]
    scenes.append(Outro())
    total = sum(s.dur for s in scenes)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    bgm = ASSETS_DIR / "bgm.mp3"
    audio_in = ["-stream_loop", "-1", "-i", str(bgm)] if bgm.exists() else \
        ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    afilter = ["-af", f"volume=0.6,afade=t=out:st={total - 1.2:.2f}:d=1.2"] if bgm.exists() else []
    cmd = [ffmpeg, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           *audio_in, "-map", "0:v", "-map", "1:a", *afilter,
           "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
           "-movflags", "+faststart", str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n = int(math.ceil(total * FPS))
    prev_last = None
    start = 0.0
    idx = 0
    for fi in range(n):
        gt = fi / FPS
        while idx < len(scenes) - 1 and gt >= start + scenes[idx].dur:
            prev_last = scenes[idx].frame(scenes[idx].dur - 1 / FPS)
            start += scenes[idx].dur
            idx += 1
        lt = gt - start
        fr = scenes[idx].frame(lt)
        if prev_last is not None and lt < XFADE:
            fr = Image.blend(prev_last, fr, lt / XFADE)
        proc.stdin.write(fr.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg 인코딩 실패")
    return out_path


def render_cover(offers: list[dict], today: date, out_path: Path, headline: str = "오늘의\n타이어 특가") -> Path:
    """쇼츠/릴스 썸네일용 정지 이미지(인트로 완성 프레임)."""
    max_pct = max(D.discount_pct(o) for o in offers)
    Intro(today, headline, len(offers), max_pct).frame(INTRO).convert("RGB").save(out_path, "JPEG", quality=92)
    return out_path
