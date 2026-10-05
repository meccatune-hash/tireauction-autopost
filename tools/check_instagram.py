"""[PC에서 실행] 인스타그램 토큰 확인 및 IG_USER_ID 찾기.

  set IG_ACCESS_TOKEN=발급받은토큰      (PowerShell: $env:IG_ACCESS_TOKEN="...")
  python tools/check_instagram.py
"""
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GRAPH_VERSION  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
tok = os.getenv("IG_ACCESS_TOKEN") or input("액세스 토큰: ").strip()
G = f"https://graph.facebook.com/{GRAPH_VERSION}"

dbg = requests.get(f"{G}/debug_token", params={"input_token": tok, "access_token": tok}).json()
d = dbg.get("data", {})
print("토큰 유효:", d.get("is_valid"), "| 만료:", d.get("expires_at") or "없음(0)", "| 권한:", ", ".join(d.get("scopes", [])))
need = {"instagram_basic", "instagram_content_publish"}
miss = need - set(d.get("scopes", []))
if miss:
    print("⚠️ 누락된 권한:", ", ".join(miss))

r = requests.get(f"{G}/me/accounts", params={"fields": "name,instagram_business_account{id,username}",
                                             "access_token": tok}).json()
for p in r.get("data", []):
    iga = p.get("instagram_business_account")
    if iga:
        print(f"페이지 '{p['name']}' → 인스타 @{iga.get('username')}  IG_USER_ID = {iga['id']}")
    else:
        print(f"페이지 '{p['name']}' → 연결된 인스타 비즈니스 계정 없음")
if "error" in r:
    print("오류:", r["error"])
