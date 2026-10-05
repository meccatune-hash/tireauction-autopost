"""캡션 / 제목 / 설명 생성.

가격·규격 같은 사실 정보는 항상 템플릿으로 넣고(환각 방지),
GEMINI_API_KEY 가 있으면 첫 줄 '후킹 문구'만 AI 로 매일 새로 씁니다.
"""
import os
import random
from datetime import date

import requests

from config import BRAND_NAME, GEMINI_MODEL, HASHTAGS, SITE_URL
from src import design as D

WEEKDAY_HEADLINES = [
    "월요일\n타이어 특가",   # 월
    "오늘의\n타이어 특가",
    "수요일\n반값 타이어",
    "오늘의\n타이어 특가",
    "주말 전\n타이어 점검",
    "주말\n타이어 특가",
    "이번 주\n타이어 특가",
]

FALLBACK_HOOKS = [
    "타이어 교체, 아직도 매장 시세 그대로 내고 계신가요? 🤔",
    "같은 타이어인데 가격이 이렇게 다를 수 있다고요? 😮",
    "바가지 걱정 없이, 세금·공임 포함 가격으로 비교하세요! ✅",
    "트레드 마모 1.6mm 이하면 교체 시기! 지금 견적 받아보세요 🛞",
    "환절기엔 타이어 공기압부터 체크! 교체할 땐 타이어옥션 🔧",
    "내 차에 딱 맞는 타이어, 검색 한 번으로 끝! 🚗",
    "오늘만큼은 타이어도 특가로 바꿔보세요 🔥",
]


def headline_for(today: date) -> str:
    return WEEKDAY_HEADLINES[today.weekday()]


def _gemini_hook(offers: list[dict], today: date) -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    items = ", ".join(f"{D.clean_title(o)} {D.discount_pct(o)}% 할인" for o in offers)
    prompt = (
        f"너는 온라인 타이어 구매 플랫폼 '{BRAND_NAME}'의 SNS 마케터야. 오늘은 {today.month}월 {today.day}일이야.\n"
        f"오늘 소개 상품: {items}\n"
        "인스타그램 게시물 첫 줄에 들어갈 후킹 문구를 한국어로 1~2문장(최대 60자) 써줘. "
        "계절/날씨/운전 상황을 자연스럽게 활용하고 이모지 1~2개를 넣어. "
        "가격 숫자, 확인 안 된 사실, 해시태그는 넣지 말고 문구만 출력해."
    )
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": key},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 1.0, "maxOutputTokens": 200}},
            timeout=40,
        )
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        return text.splitlines()[0][:120] if text else None
    except Exception as e:  # AI 실패해도 게시는 계속
        print(f"[caption] Gemini 실패, 기본 문구 사용: {e}")
        return None


def _item_lines(o: dict) -> str:
    lines = [f"{D.clean_title(o)} ({D.spec_line(o)})"]
    if o.get("listPrice") and o["listPrice"] > o["unitPrice"]:
        lines.append(f"   {D.won(o['listPrice'])} → {D.won(o['unitPrice'])} ({D.discount_pct(o)}%↓, 1본)")
    else:
        lines.append(f"   {D.won(o['unitPrice'])} (1본)")
    return "\n".join(lines)


def _tags(offers) -> list[str]:
    brands = []
    for o in offers:
        b = f"#{(o.get('brand') or '').strip()}타이어"
        if b != "#타이어" and b not in brands:
            brands.append(b)
    return HASHTAGS + brands


def build(featured: dict, video_items: list[dict], today: date) -> dict:
    hook = _gemini_hook(video_items, today) or random.Random(today.toordinal()).choice(FALLBACK_HOOKS)
    site = SITE_URL.replace("https://", "")
    footer = (f"\n👉 앱에서 '{BRAND_NAME}' 검색 또는 {site}\n"
              "※ 가격·재고는 판매자 사정에 따라 변동될 수 있어요.")

    perks = []
    if (featured.get("deliveryFee") or 0) == 0:
        perks.append("무료배송")
    if featured.get("installFee"):
        perks.append(f"장착비 {D.won(featured['installFee'])}")

    ig_image = "\n".join([
        hook, "",
        f"🔥 오늘의 특가 | {D.clean_title(featured)}",
        f"📏 {D.spec_line(featured)} · {D.season_label(featured) or '타이어'}",
        f"💰 {D.won(featured.get('listPrice') or featured['unitPrice'])} → {D.won(featured['unitPrice'])}"
        f" ({D.discount_pct(featured)}% 할인, 1본 기준)",
        *( [f"🔧 {' · '.join(perks)}"] if perks else [] ),
        footer, "",
        " ".join(_tags([featured])),
    ])

    numbered = "\n".join(f"{i + 1}️⃣ {_item_lines(o)}" for i, o in enumerate(video_items))
    max_pct = max(D.discount_pct(o) for o in video_items)
    ig_reel = "\n".join([hook, "", f"📢 {today.month}/{today.day} 타이어 특가 TOP {len(video_items)}", "",
                         numbered, footer, "", " ".join(_tags(video_items))])

    yt_title = f"오늘의 타이어 특가 TOP{len(video_items)} | 최대 {max_pct}% 할인 🔥 {today.month}/{today.day} #Shorts"
    yt_desc = "\n".join([hook, "", numbered, "",
                         f"🛞 {BRAND_NAME} - 바가지 걱정 끝! 믿고 바꾸는 안심 교체",
                         f"내 차에 맞는 타이어를 검색하고 주변 장착점 견적을 비교해 보세요.",
                         f"🌐 {SITE_URL}", "※ 가격·재고는 변동될 수 있습니다.", "",
                         " ".join(_tags(video_items) + ["#Shorts"])])
    yt_tags = [t.lstrip("#") for t in _tags(video_items)] + ["타이어 싸게 사는 법", "타이어 가격 비교"]

    return {"hook": hook, "ig_image": ig_image[:2200], "ig_reel": ig_reel[:2200],
            "yt_title": yt_title[:100], "yt_description": yt_desc[:4900], "yt_tags": yt_tags}
