"""매일 실행: 상품 수집 → 이미지·영상 생성 → 인스타그램/유튜브 업로드.

사용법
  python main.py --dry-run          # 생성만 (업로드 안 함) → out/날짜/ 확인
  python main.py                    # 생성 + 전체 업로드
  python main.py --only youtube     # 특정 플랫폼만 (instagram_image, instagram_reel, youtube)

같은 날 다시 실행하면 이미 성공한 플랫폼은 건너뜁니다(중복 게시 방지).
"""
import argparse
import json
import sys
import traceback
from datetime import datetime

from config import KST, OUT_DIR, VIDEO_ITEM_COUNT
from src import caption, design, scrape, state as st
from src.render_image import render_feed_image
from src.render_video import render_cover, render_video

PLATFORMS = ["instagram_image", "instagram_reel", "youtube"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=PLATFORMS, action="append")
    args = ap.parse_args()

    today = datetime.now(KST).date()
    out = OUT_DIR / today.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    design.ensure_fonts()

    state = st.load()
    day = st.day_entry(state, today)
    targets = [p for p in (args.only or PLATFORMS) if not day["results"].get(p)]
    if not args.dry_run and not targets:
        print(f"[main] {today} 게시가 이미 모두 완료되었습니다.")
        return 0

    offers = scrape.fetch_offers()
    by_id = {o["offerId"]: o for o in offers}
    # 같은 날 재실행 시 같은 상품 유지
    picks = [by_id[i] for i in day.get("picks", []) if i in by_id]
    if len(picks) < min(VIDEO_ITEM_COUNT, len(offers)):
        picks = st.choose(offers, state, today, VIDEO_ITEM_COUNT)
    day["picks"] = [o["offerId"] for o in picks]
    featured = picks[0]
    print("[main] 오늘의 상품:", ", ".join(design.clean_title(o) for o in picks))

    headline = caption.headline_for(today)
    img = render_feed_image(featured, out / "feed.jpg")
    cover = render_cover(picks, today, out / "cover.jpg", headline)
    vid = render_video(picks, today, out / "reel.mp4", headline)
    caps = caption.build(featured, picks, today)
    (out / "captions.json").write_text(json.dumps(caps, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[main] 생성 완료: {img.name}, {vid.name} ({vid.stat().st_size / 1e6:.1f}MB)")

    if args.dry_run:
        print(f"[main] --dry-run: 업로드 생략. 결과물 폴더: {out}")
        return 0

    from src import media_host, upload_instagram as ig, upload_youtube as yt

    errors = []

    def run(name, fn):
        if name not in targets:
            return
        try:
            res = fn()
            day["results"][name] = res
            print(f"[{name}] 성공: {res}")
        except Exception as e:
            traceback.print_exc()
            errors.append(f"{name}: {e}")
        finally:
            st.save(state)

    stamp = today.isoformat()
    cover_url = None

    def ig_image():
        url = media_host.publish(img, f"{stamp}/feed.jpg")
        return ig.post_image(url, caps["ig_image"])

    def ig_reel():
        nonlocal cover_url
        try:
            cover_url = media_host.publish(cover, f"{stamp}/cover.jpg")
        except Exception as e:
            print(f"[instagram_reel] 커버 업로드 실패(무시): {e}")
        return ig.post_reel(vid, caps["ig_reel"], cover_url)

    def youtube():
        return yt.upload_short(vid, caps["yt_title"], caps["yt_description"], caps["yt_tags"])

    run("instagram_image", ig_image)
    run("instagram_reel", ig_reel)
    run("youtube", youtube)

    if any(day["results"].get(p) for p in PLATFORMS):
        st.mark_used(state, picks, today)
    st.save(state)

    if errors:
        print("[main] 실패한 항목:\n  " + "\n  ".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
