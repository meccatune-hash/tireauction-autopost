import json
import re
import requests
from config import CATALOG_PATHS, SITE_URL

UA = {"User-Agent": "Mozilla/5.0"}
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)

def fetch_fallback_offers() -> list[dict]:
    seen = {}
    for path in CATALOG_PATHS:
        try:
            r = requests.get(SITE_URL + path, headers=UA, timeout=30)
            if not r.ok:
                continue
            payload = "".join(json.loads('"' + c + '"') for c in _PUSH_RE.findall(r.text))
            dec = json.JSONDecoder()
            idx = 0
            while True:
                idx = payload.find('{"offerId"', idx)
                if idx < 0:
                    break
                try:
                    obj, end = dec.raw_decode(payload, idx)
                    if obj.get("images") and (obj.get("unitPrice") or 0) > 0:
                        seen.setdefault(obj["offerId"], obj)
                    idx = end
                except Exception:
                    idx += 10
        except Exception as e:
            print(f"[fallback] {path} 실패: {e}")
    return list(seen.values())
