"""인스타그램 피드용 1080x1350 (4:5) 홍보 이미지."""
from pathlib import Path

from PIL import Image, ImageDraw

from config import BRAND_NAME, SITE_URL, TAGLINE
from src import design as D
from src.scrape import image_url

W, H = 1080, 1350


def render_feed_image(o: dict, out_path: Path, headline: str = "오늘의 특가") -> Path:
    im = Image.new("RGBA", (W, H), D.CREAM + (255,))
    d = ImageDraw.Draw(im)

    # 헤더
    d.rectangle((0, 0, W, 210), fill=D.ORANGE)
    d.text((60, 46), BRAND_NAME, font=D.font("Black", 64), fill=D.WHITE)
    d.text((62, 132), TAGLINE, font=D.font("SemiBold", 30), fill=(255, 232, 216))
    hf = D.font("ExtraBold", 34)
    hw = D.text_w(hf, headline) + 48
    D.pill(d, (W - 60 - hw, 70), headline, hf, D.ORANGE, D.WHITE, pad_x=24, pad_y=14)

    # 상품 카드
    card = (60, 260, W - 60, 880)
    D.shadowed_card(im, card, 44)
    prod = D.fit_into(D.trim(D.fetch_image(image_url(o))), 820, 540)
    cx = (card[0] + card[2]) // 2 - prod.width // 2
    cy = (card[1] + card[3]) // 2 - prod.height // 2
    im.alpha_composite(prod, (cx, cy))

    pct = D.discount_pct(o)
    if pct >= 5:
        badge = D.discount_badge(210, pct)
        im.alpha_composite(badge, (W - 60 - 170, 215))

    d = ImageDraw.Draw(im)
    # 브랜드 / 시즌 칩
    x = 60
    y = 920
    chip = D.font("Bold", 30)
    x = D.pill(d, (x, y), o.get("brand") or "", chip, D.WHITE, D.DARK, pad_x=20, pad_y=8) + 12
    if D.season_label(o):
        x = D.pill(d, (x, y), D.season_label(o), chip, D.ORANGE_DARK, D.CREAM, pad_x=20, pad_y=8,
                   outline=D.ORANGE) + 12
    if o.get("origin"):
        D.pill(d, (x, y), f"{o['origin']}산", chip, D.GREY, D.CREAM, pad_x=20, pad_y=8, outline=D.LIGHT_GREY)

    # 상품명 / 규격
    tf = D.fit_font(D.clean_title(o), "ExtraBold", 62, W - 120, 40)
    d.text((60, 990), D.clean_title(o), font=tf, fill=D.DARK)
    d.text((62, 1070), D.spec_line(o), font=D.font("SemiBold", 36), fill=D.GREY)

    # 가격
    py = 1130
    if o.get("listPrice") and o["listPrice"] > o["unitPrice"]:
        D.strike_text(d, (62, py + 30), D.won(o["listPrice"]), D.font("Medium", 38), D.GREY)
        px = 62 + D.text_w(D.font("Medium", 38), D.won(o["listPrice"])) + 28
    else:
        px = 60
    pf = D.font("Black", 84)
    d.text((px, py), D.won(o["unitPrice"]), font=pf, fill=D.ORANGE)
    ux = px + D.text_w(pf, D.won(o["unitPrice"])) + 12
    d.text((ux, py + 44), "/ 1본", font=D.font("SemiBold", 32), fill=D.GREY)

    # 혜택 줄
    perks = []
    if (o.get("deliveryFee") or 0) == 0:
        perks.append("무료배송")
    if o.get("installFee"):
        perks.append(f"장착비 {D.won(o['installFee'])}")
    if perks:
        pf2 = D.font("SemiBold", 28)
        txt = "  ·  ".join(perks)
        d.text((W - 60 - D.text_w(pf2, txt), 1088), txt, font=pf2, fill=D.ORANGE_DARK)

    # 하단 CTA
    d.rectangle((0, H - 100, W, H), fill=D.DARK)
    cta = f"앱에서 '{BRAND_NAME}' 검색   |   {SITE_URL.replace('https://', '')}"
    cf = D.fit_font(cta, "Bold", 34, W - 100)
    d.text(((W - D.text_w(cf, cta)) // 2, H - 72), cta, font=cf, fill=D.WHITE)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out_path, "JPEG", quality=93)
    return out_path
