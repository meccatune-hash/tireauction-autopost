"""YouTube Data API v3 쇼츠 업로드 (OAuth 리프레시 토큰 방식).

필요 환경변수: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
리프레시 토큰은 tools/get_youtube_token.py 를 PC 에서 1회 실행해 발급합니다.
"""
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import YT_PRIVACY

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _client():
    cid, sec, rt = (os.getenv(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not all((cid, sec, rt)):
        raise RuntimeError("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN 환경변수가 없습니다.")
    creds = Credentials(None, refresh_token=rt, client_id=cid, client_secret=sec,
                        token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_short(video_path: Path, title: str, description: str, tags: list[str]) -> dict:
    yt = _client()
    body = {
        "snippet": {"title": title, "description": description, "tags": tags[:30],
                    "categoryId": "2", "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
        "status": {"privacyStatus": YT_PRIVACY, "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video_path), mimetype="video/mp4",
                                                        chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}", "privacy": resp["status"]["privacyStatus"]}
