"""인스타그램 이미지 게시에 필요한 '공개 URL' 을 만들기 위해
생성된 이미지를 같은 GitHub 저장소의 media 브랜치에 올립니다.

GitHub Actions 안에서는 GITHUB_REPOSITORY / GITHUB_TOKEN 이 자동 제공됩니다.
※ raw.githubusercontent.com 은 공개(Public) 저장소에서만 외부 접근이 됩니다.
"""
import base64
import os
import time
from pathlib import Path

import requests

from config import MEDIA_BRANCH

API = "https://api.github.com"


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}


def _ensure_branch(repo: str, tok: str) -> None:
    r = requests.get(f"{API}/repos/{repo}/git/ref/heads/{MEDIA_BRANCH}", headers=_h(tok), timeout=30)
    if r.status_code == 200:
        return
    default = requests.get(f"{API}/repos/{repo}", headers=_h(tok), timeout=30).json()["default_branch"]
    sha = requests.get(f"{API}/repos/{repo}/git/ref/heads/{default}", headers=_h(tok),
                       timeout=30).json()["object"]["sha"]
    requests.post(f"{API}/repos/{repo}/git/refs", headers=_h(tok), timeout=30,
                  json={"ref": f"refs/heads/{MEDIA_BRANCH}", "sha": sha}).raise_for_status()


def publish(local: Path, dest: str) -> str:
    repo, tok = os.getenv("GITHUB_REPOSITORY"), os.getenv("GITHUB_TOKEN")
    if not repo or not tok:
        raise RuntimeError("GITHUB_REPOSITORY / GITHUB_TOKEN 이 없습니다 (GitHub Actions 에서 실행하세요).")
    _ensure_branch(repo, tok)
    url = f"{API}/repos/{repo}/contents/{dest}"
    body = {"message": f"media: {dest}", "branch": MEDIA_BRANCH,
            "content": base64.b64encode(Path(local).read_bytes()).decode()}
    ex = requests.get(url, headers=_h(tok), params={"ref": MEDIA_BRANCH}, timeout=30)
    if ex.status_code == 200:
        body["sha"] = ex.json()["sha"]
    requests.put(url, headers=_h(tok), json=body, timeout=60).raise_for_status()
    public = f"https://raw.githubusercontent.com/{repo}/{MEDIA_BRANCH}/{dest}"
    # CDN 반영 대기
    for _ in range(10):
        if requests.head(public, timeout=20).status_code == 200:
            return public
        time.sleep(3)
    raise RuntimeError(f"공개 URL 접근 불가: {public} (저장소가 Public 인지 확인하세요)")
