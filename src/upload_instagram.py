"""Instagram Graph API 업로드 (Facebook 로그인 방식, 비즈니스/크리에이터 계정).

필요 환경변수
  IG_USER_ID       : 인스타 비즈니스 계정 ID (tools/check_instagram.py 로 확인)
  IG_ACCESS_TOKEN  : 장기 토큰 (권장: 비즈니스 관리자 '시스템 사용자' 토큰 - 만료 없음)
권한: instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement
"""
import os
import time
from pathlib import Path

import requests

from config import GRAPH_VERSION

GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"


def _env():
    uid, tok = os.getenv("IG_USER_ID"), os.getenv("IG_ACCESS_TOKEN")
    if not uid or not tok:
        raise RuntimeError("IG_USER_ID / IG_ACCESS_TOKEN 환경변수가 없습니다.")
    return uid, tok


def _check(r: requests.Response) -> dict:
    try:
        data = r.json()
    except ValueError:
        r.raise_for_status()
        raise
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram API 오류: {data.get('error', data)}")
    return data


def _wait(container_id: str, tok: str, timeout: int = 600) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = _check(requests.get(f"{GRAPH}/{container_id}", params={"fields": "status_code,status",
                                                                    "access_token": tok}, timeout=30))
        sc = d.get("status_code")
        if sc == "FINISHED":
            return
        if sc in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"미디어 처리 실패: {d}")
        time.sleep(6)
    raise TimeoutError("Instagram 미디어 처리 시간 초과")


def _publish(uid: str, tok: str, creation_id: str) -> dict:
    d = _check(requests.post(f"{GRAPH}/{uid}/media_publish",
                             data={"creation_id": creation_id, "access_token": tok}, timeout=60))
    media_id = d["id"]
    link = _check(requests.get(f"{GRAPH}/{media_id}", params={"fields": "permalink", "access_token": tok},
                               timeout=30)).get("permalink")
    return {"id": media_id, "permalink": link}


def post_image(image_url: str, caption: str) -> dict:
    """image_url 은 인스타 서버가 접근할 수 있는 공개 URL(JPEG) 이어야 합니다."""
    uid, tok = _env()
    c = _check(requests.post(f"{GRAPH}/{uid}/media",
                             data={"image_url": image_url, "caption": caption, "access_token": tok},
                             timeout=60))["id"]
    _wait(c, tok, 180)
    return _publish(uid, tok, c)


def post_reel(video_path: Path, caption: str, cover_url: str | None = None) -> dict:
    """로컬 파일을 resumable 방식으로 직접 업로드 (공개 URL 불필요)."""
    uid, tok = _env()
    data = {"media_type": "REELS", "upload_type": "resumable", "caption": caption,
            "share_to_feed": "true", "access_token": tok}
    if cover_url:
        data["cover_url"] = cover_url
    c = _check(requests.post(f"{GRAPH}/{uid}/media", data=data, timeout=60))["id"]
    blob = Path(video_path).read_bytes()
    _check(requests.post(
        f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{c}",
        headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(blob))},
        data=blob, timeout=600,
    ))
    _wait(c, tok, 900)
    return _publish(uid, tok, c)
