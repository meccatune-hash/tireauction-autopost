"""GitHub 저장소(meccatune-hash/tireauction-autopost)에 Secrets를 자동으로 등록하는 스크립트.

사용법:
  1) .env 파일에 키를 적어두거나,
  2) 실행 후 콘솔에서 복사+붙여넣기 하면 자동으로 GitHub Secrets에 등록됩니다.

  python tools/set_secrets.py
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = "meccatune-hash/tireauction-autopost"
GH_PATH = r"C:\Program Files\GitHub CLI\gh.exe"


def get_token() -> str:
    res = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True)
    for line in res.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return ""


def set_secret(name: str, value: str, gh_token: str):
    if not value or not value.strip():
        return False
    val = value.strip()
    env = os.environ.copy()
    env["GH_TOKEN"] = gh_token
    proc = subprocess.run([GH_PATH, "secret", "set", name, "-R", REPO],
                          input=val, text=True, capture_output=True, env=env)
    if proc.returncode == 0:
        print(f"  [OK] {name} 등록 완료")
        return True
    else:
        print(f"  [실패] {name}: {proc.stderr}")
        return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=" * 60)
    print(" GitHub Secrets 자동 등록 도구")
    print(f" 대상 저장소: https://github.com/{REPO}")
    print("=" * 60)

    gh_token = get_token()
    if not gh_token:
        print("GitHub 토큰을 찾을 수 없습니다.")
        return 1

    # .env 파일이 있으면 읽기
    env_file = Path(".env")
    env_vals = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vals[k.strip()] = v.strip().strip('"').strip("'")

    keys = [
        ("IG_USER_ID", "인스타그램 비즈니스 계정 ID"),
        ("IG_ACCESS_TOKEN", "인스타그램/메타 시스템 사용자 액세스 토큰"),
        ("YT_CLIENT_ID", "유튜브 OAuth Client ID"),
        ("YT_CLIENT_SECRET", "유튜브 OAuth Client Secret"),
        ("YT_REFRESH_TOKEN", "유튜브 OAuth Refresh Token"),
        ("GEMINI_API_KEY", "Gemini API 키 (선택사항, 없으면 Enter)"),
    ]

    for k, desc in keys:
        val = env_vals.get(k)
        if not val:
            val = input(f"\n{desc} ({k}) 입력 [건너뛰려면 Enter]: ").strip()
        if val:
            set_secret(k, val, gh_token)
        else:
            print(f"  [-] {k} 건너뜀")

    print("\n등록 완료! GitHub 저장소 Settings -> Secrets and variables -> Actions 에서 확인할 수 있습니다.")


if __name__ == "__main__":
    main()
