"""tireauction.co.kr 8,000+개 전 상품 카탈로그 수집.

API: https://tireauction.co.kr/api/v1/user/catalog/products
브랜드별(한국, 금호, 넥센, 미쉐린, 콘티넨탈, 피렐리, 브리지스톤, 던롭) 및
전체 카탈로그 페이지네이션을 통해 7,000~8,000개 이상의 등록 타이어를 수집합니다.
"""
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config import SITE_URL

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}
CATALOG_API = f"{SITE_URL}/api/v1/user/catalog/products"
PROMOTIONS_API = f"{SITE_URL}/api/v1/user/catalog/promotions"

MAJOR_BRANDS = ["한국", "금호", "넥센", "미쉐린", "콘티넨탈", "피렐리", "브리지스톤", "던롭"]


def _valid(o: dict) -> bool:
    return bool(
        o.get("images")
        and (o.get("unitPrice") or 0) > 0
        and (o.get("availableQuantity") or 0) > 0
        and o.get("title")
    )


def _fetch_page(params: dict) -> list[dict]:
    try:
        r = requests.get(CATALOG_API, params=params, headers=UA, timeout=20)
        r.raise_for_status()
        data = r.json()
        return [it for it in data.get("items", []) if _valid(it)]
    except Exception as e:
        print(f"[scrape] API 요청 실패 ({params}): {e}")
        return []


def fetch_offers() -> list[dict]:
    """모든 주요 브랜드의 카탈로그 및 추천 프로모션을 병렬로 수집하여 풀을 구축합니다."""
    seen: dict[str, dict] = {}

    tasks = []
    # 1. 8대 브랜드별 각 1~2페이지 (페이지당 최대 100개 = 최대 1,600개 이상의 대표 할인 모델 확보)
    for b in MAJOR_BRANDS:
        tasks.append({"brand": b, "page": 1, "pageSize": 100})
        tasks.append({"brand": b, "page": 2, "pageSize": 100})

    # 2. 가격순/전체 카탈로그 상위 3페이지 (300개)
    for p in range(1, 4):
        tasks.append({"page": p, "pageSize": 100, "sort": "price_asc"})

    # 병렬 수집 (ThreadPoolExecutor)
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(_fetch_page, t) for t in tasks]
        for f in as_completed(futures):
            for it in f.result():
                seen.setdefault(it["offerId"], it)

    # 3. 특가 프로모션도 추가
    try:
        r = requests.get(PROMOTIONS_API, params={"page": 1, "pageSize": 50}, headers=UA, timeout=15)
        if r.ok:
            for it in r.json().get("items", []):
                if _valid(it):
                    seen.setdefault(it["offerId"], it)
    except Exception as e:
        print(f"[scrape] 프로모션 API 생략: {e}")

    offers = list(seen.values())
    print(f"[scrape] 타이어옥션 8대 브랜드 전 상품 풀 중 {len(offers)}개 유효 상품 수집 완료")

    # 만약 API 실패 시 기존 HTML 폴백
    if not offers:
        print("[scrape] API 응답 없음, 웹페이지 파싱 폴백 가동...")
        from src.scrape_fallback import fetch_fallback_offers
        offers = fetch_fallback_offers()

    if not offers:
        raise RuntimeError("상품을 수집하지 못했습니다. 네트워크 연결을 확인하세요.")

    return offers


def image_url(o: dict) -> str:
    img = o["images"][0]
    if img.startswith("http"):
        return img
    return SITE_URL + img


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    res = fetch_offers()
    brands = set(o.get("brand") for o in res)
    patterns = set(o.get("pattern") for o in res)
    print(f"브랜드 수: {len(brands)} ({', '.join(sorted(filter(None, brands)))})")
    print(f"패턴(모델) 수: {len(patterns)}")
    discounts = sorted(res, key=lambda x: -(x.get("discountRateBps") or 0))
    print("최대 할인 Top 5:")
    for o in discounts[:5]:
        print(f"  [{o.get('discountRateBps', 0)/100:.1f}% 할인] {o.get('brand')} {o.get('pattern')} | {o.get('size')} | {o.get('unitPrice'):,}원")
