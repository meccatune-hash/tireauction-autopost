"""tireauction.co.kr 상품(오퍼) 수집.

목록 페이지는 Next.js 서버 렌더링이며, 상품 데이터가 RSC 페이로드
(self.__next_f.push) 안에 JSON 으로 포함되어 있습니다.
"""
import json
import re

import requests

from config import CATALOG_PATHS, SITE_URL

UA = {"User-Agent": "Mozilla/5.0 (compatible; TireAuctionAutoPost/1.0)"}
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)


def _decode_payload(html: str) -> str:
    return "".join(json.loads('"' + c + '"') for c in _PUSH_RE.findall(html))


def _extract_offers(payload: str) -> list[dict]:
    dec = json.JSONDecoder()
    offers, idx = [], 0
    while True:
        idx = payload.find('{"offerId"', idx)
        if idx < 0:
            break
        try:
            obj, end = dec.raw_decode(payload, idx)
            offers.append(obj)
            idx = end
        except json.JSONDecodeError:
            idx += 10
    return offers


def _valid(o: dict) -> bool:
    return bool(
        o.get("images")
        and (o.get("unitPrice") or 0) > 0
        and (o.get("availableQuantity") or 0) > 0
        and o.get("title")
    )


def fetch_offers() -> list[dict]:
    seen: dict[str, dict] = {}
    for path in CATALOG_PATHS:
        try:
            r = requests.get(SITE_URL + path, headers=UA, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"[scrape] {path} 실패: {e}")
            continue
        for o in _extract_offers(_decode_payload(r.text)):
            if _valid(o):
                seen.setdefault(o["offerId"], o)
    offers = list(seen.values())
    print(f"[scrape] 유효 상품 {len(offers)}개 수집")
    if not offers:
        raise RuntimeError("상품을 하나도 수집하지 못했습니다. 사이트 구조가 바뀌었는지 확인하세요.")
    return offers


def image_url(o: dict) -> str:
    return SITE_URL + o["images"][0]


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for o in fetch_offers():
        print(o["discountRateBps"], o["brand"], o["title"], o["size"], o["unitPrice"])
