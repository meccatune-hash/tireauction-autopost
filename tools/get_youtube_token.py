"""[PC에서 1회 실행] 유튜브 업로드용 리프레시 토큰 발급.

1) Google Cloud Console 에서 'YouTube Data API v3' 사용 설정
2) OAuth 동의 화면 구성 → 게시 상태를 '프로덕션'으로 (테스트 상태면 토큰이 7일 후 만료)
3) 사용자 인증 정보 → OAuth 클라이언트 ID (유형: 데스크톱 앱) → JSON 다운로드
4) 이 폴더에 client_secret.json 으로 저장 후:
     python tools/get_youtube_token.py
5) 브라우저에서 '타이어옥션' 유튜브 채널 계정으로 로그인/허용
6) 출력된 3개 값을 GitHub Secrets 에 등록
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
secret = Path(sys.argv[1] if len(sys.argv) > 1 else "client_secret.json")
if not secret.exists():
    sys.exit(f"{secret} 파일이 없습니다. 위 안내 3)번을 먼저 진행하세요.")

flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
info = json.loads(secret.read_text(encoding="utf-8"))
info = info.get("installed") or info.get("web")
print("\n=== GitHub Secrets 에 아래 값을 등록하세요 ===")
print("YT_CLIENT_ID     =", info["client_id"])
print("YT_CLIENT_SECRET =", info["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
