"""전역 설정. 민감 정보는 모두 환경변수(GitHub Secrets)로 주입합니다."""
import os
from datetime import timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
FONT_DIR = ASSETS_DIR / "fonts"
OUT_DIR = ROOT / "out"
CACHE_DIR = OUT_DIR / "_cache"
STATE_FILE = ROOT / "state" / "posted.json"

KST = timezone(timedelta(hours=9))

# ── 사이트 ───────────────────────────────────────────────
SITE_URL = "https://tireauction.co.kr"
# 상품 목록을 수집할 페이지 (중복 상품은 자동 제거)
CATALOG_PATHS = ["/tires?cat=car", "/tires?cat=suv", "/tires"]

# ── 브랜드 ───────────────────────────────────────────────
BRAND_NAME = "타이어옥션"
TAGLINE = "바가지 걱정 끝! 믿고 바꾸는 안심 교체"
SUB_TAGLINE = "내 차에 딱 맞는 타이어, 한눈에 비교"
HASHTAGS = [
    "#타이어옥션", "#타이어", "#타이어교체", "#타이어할인", "#타이어추천",
    "#타이어가격", "#자동차관리", "#타이어장착", "#자동차", "#카스타그램",
]

# ── 콘텐츠 선택 ─────────────────────────────────────────
VIDEO_ITEM_COUNT = 4          # 영상에 소개할 상품 수
REPEAT_COOLDOWN_DAYS = 21     # 같은 상품을 다시 소개하기까지 최소 일수

# ── 업로드 ───────────────────────────────────────────────
GRAPH_VERSION = os.getenv("GRAPH_API_VERSION", "v23.0")
YT_PRIVACY = os.getenv("YT_PRIVACY", "public")  # public | unlisted | private
MEDIA_BRANCH = os.getenv("MEDIA_BRANCH", "media")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
