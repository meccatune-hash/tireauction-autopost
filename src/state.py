"""게시 이력(state/posted.json) 관리 및 오늘 소개할 상품 선택."""
import json
from datetime import date, timedelta

from config import REPEAT_COOLDOWN_DAYS, STATE_FILE
from src.design import discount_pct


def load() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"days": {}, "last_featured": {}}


def save(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # 이력은 최근 120일만 유지
    days = state.get("days", {})
    for k in sorted(days)[:-120]:
        days.pop(k)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def day_entry(state: dict, today: date) -> dict:
    return state.setdefault("days", {}).setdefault(today.isoformat(), {"picks": [], "results": {}})


def _group(o: dict) -> str:
    """같은 패턴의 사이즈만 다른 상품은 한 그룹으로 본다(다양성 확보)."""
    return f"{o.get('brand', '')}|{(o.get('pattern') or o.get('title', '')).strip().lower()}"


def choose(offers: list[dict], state: dict, today: date, n: int) -> list[dict]:
    """패턴별 가장 할인율 높은 상품 1개씩 → 최근에 안 쓴 패턴 우선 → 할인율 순."""
    best: dict[str, dict] = {}
    for o in offers:
        g = _group(o)
        if g not in best or discount_pct(o) > discount_pct(best[g]):
            best[g] = o

    last = state.get("last_featured", {})
    cutoff = (today - timedelta(days=REPEAT_COOLDOWN_DAYS)).isoformat()

    def key(o):
        lu = last.get(_group(o), "")
        fresh = lu < cutoff  # 쿨다운 지난(또는 처음) 패턴 우선
        return (not fresh, lu, -discount_pct(o))

    ranked = sorted(best.values(), key=key)
    picks = ranked[:n]
    # 패턴 종류가 n개보다 적으면 할인율 높은 다른 사이즈로 채움
    if len(picks) < n:
        used = {p["offerId"] for p in picks}
        rest = sorted((o for o in offers if o["offerId"] not in used), key=lambda o: -discount_pct(o))
        picks += rest[: n - len(picks)]
    return picks


def mark_used(state: dict, picks: list[dict], today: date) -> None:
    lf = state.setdefault("last_featured", {})
    for o in picks:
        lf[_group(o)] = today.isoformat()
