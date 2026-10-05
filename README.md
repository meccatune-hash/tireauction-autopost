# 타이어옥션 SNS 자동 홍보

매일 오전 10시(KST)에 자동으로 실행됩니다.

1. **수집**: [tireauction.co.kr](https://tireauction.co.kr) 상품 목록(브랜드·규격·정가·할인가·이미지)을 가져옵니다.
2. **선택**: 할인율이 높은 상품을 고르되, 최근 21일 안에 소개한 타이어 패턴은 뒤로 미룹니다.
3. **생성**
   - 인스타그램 피드 이미지 1장 (1080×1350)
   - 세로 영상 1개 (1080×1920, 약 20초, TOP 4 상품) → 인스타 릴스 + 유튜브 쇼츠
   - 캡션·제목·해시태그 (가격 정보는 템플릿, 첫 줄 문구는 Gemini AI가 선택적으로 작성)
4. **업로드**: 인스타 피드, 인스타 릴스, 유튜브 쇼츠

실행은 **GitHub Actions**에서 하기 때문에 PC를 꺼 둬도 됩니다. 같은 날 다시 실행하면 이미 성공한 플랫폼은 건너뛰어서 중복으로 올라가지 않습니다.

---

## 1회 설정 (약 30~60분)

### ① GitHub 저장소
1. GitHub에서 **Public** 저장소를 새로 만듭니다 (예: `tireauction-autopost`).
   - 인스타그램 API는 이미지를 *공개 URL*로만 받습니다. 그래서 생성된 이미지를 이 저장소의 `media` 브랜치에 올려서 공개 URL을 만듭니다.
   - 토큰 같은 비밀값은 저장소 코드가 아니라 Secrets에 저장되므로 Public이어도 노출되지 않습니다.
2. 이 폴더를 push합니다.
   ```powershell
   git remote add origin https://github.com/<계정>/tireauction-autopost.git
   git push -u origin main
   ```

### ② 인스타그램 (Meta Graph API)
1. [Meta for Developers](https://developers.facebook.com/apps)에서 앱을 만듭니다 (유형: **비즈니스**). **Instagram Graph API** 제품을 추가합니다.
2. **권장: 만료되지 않는 시스템 사용자 토큰을 씁니다.**
   [비즈니스 설정](https://business.facebook.com/settings) → 사용자 → **시스템 사용자** 추가(관리자) → *자산 할당*에서 페이스북 페이지와 인스타 계정을 추가합니다 → **토큰 생성**(앱 선택) 후 다음 권한을 체크합니다.
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`
3. IG_USER_ID를 확인합니다.
   ```powershell
   .\.venv\Scripts\python tools\check_instagram.py
   ```
   출력된 `IG_USER_ID = 1784...` 값을 메모해 둡니다.

### ③ 유튜브 (YouTube Data API v3)
1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 만들고 **YouTube Data API v3**를 *사용 설정*합니다.
2. **OAuth 동의 화면**에서 외부 앱을 만듭니다. 만든 뒤 게시 상태를 **"프로덕션으로 푸시"**로 바꿉니다.
   > 테스트 상태로 두면 토큰이 7일 뒤 만료되어 업로드가 멈춥니다.
3. 사용자 인증 정보 → **OAuth 클라이언트 ID** (애플리케이션 유형: *데스크톱 앱*)를 만들고 JSON을 다운로드합니다. 이 폴더에 `client_secret.json`으로 저장합니다.
4. 리프레시 토큰을 발급합니다. 브라우저가 열리면 **타이어옥션 채널 계정**을 선택합니다.
   ```powershell
   .\.venv\Scripts\python tools\get_youtube_token.py
   ```

> [!IMPORTANT]
> 새로 만든 Google API 프로젝트는 **감사(audit)를 통과하기 전까지 API로 올린 영상이 '비공개'로 고정**됩니다.
> [YouTube API 감사 신청서](https://support.google.com/youtube/contact/yt_api_form)를 꼭 제출하세요(보통 수일~수주 소요).
> 승인 전에는 영상이 비공개로 올라가므로 YouTube Studio에서 직접 공개로 바꿔야 합니다.

### ④ (선택) Gemini API 키
[Google AI Studio](https://aistudio.google.com/apikey)에서 키를 발급합니다. 키가 있으면 날마다 새 후킹 문구를 쓰고, 없으면 내장 문구 7개를 돌아가며 씁니다.

### ⑤ GitHub Secrets 등록
저장소 → Settings → Secrets and variables → Actions → **New repository secret**

| 이름 | 값 |
|---|---|
| `IG_USER_ID` | ②-3에서 확인한 값 |
| `IG_ACCESS_TOKEN` | ②-2 시스템 사용자 토큰 |
| `YT_CLIENT_ID` | ③-4 출력값 |
| `YT_CLIENT_SECRET` | ③-4 출력값 |
| `YT_REFRESH_TOKEN` | ③-4 출력값 |
| `GEMINI_API_KEY` | (선택) |

### ⑥ 테스트
1. 저장소 → **Actions** → "타이어옥션 매일 자동 홍보" → **Run workflow** → `dry_run` 체크 후 실행합니다.
2. 끝나면 실행 결과 하단 **Artifacts**에서 이미지, 영상, 캡션을 내려받아 확인합니다.
3. 문제가 없으면 `dry_run`을 끄고 한 번 실행합니다. 실제로 게시됩니다.
4. 이후에는 매일 10시에 자동 실행됩니다. 실패하면 GitHub가 이메일로 알려 줍니다.

---

## 로컬에서 미리 보기
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python main.py --dry-run     # out\날짜\ 폴더에 feed.jpg, reel.mp4, captions.json 생성
```

## 커스터마이징
| 항목 | 위치 |
|---|---|
| 게시 시간 | `.github/workflows/daily.yml`의 `cron` (UTC 기준, KST = UTC+9) |
| 배경음악 | `assets/bgm.mp3`에 파일을 넣으면 자동 적용됩니다. **저작권 없는 음원**만 쓰세요(예: YouTube 오디오 라이브러리). 없으면 무음으로 만듭니다. |
| 해시태그·문구·영상 상품 수 | `config.py` |
| 요일별 헤드라인, 기본 후킹 문구 | `src/caption.py` |
| 디자인 | `src/render_image.py`, `src/render_video.py` |

## 문제 해결
- **상품을 하나도 수집하지 못함**: 사이트 구조가 바뀐 경우입니다. `src/scrape.py`를 확인하세요.
- **Instagram `(#10) ... permission`**: 토큰 권한이 빠졌거나, 인스타 계정이 페이지에 연결되지 않은 경우입니다.
- **Instagram 이미지 URL 오류**: 저장소가 Public인지 확인하세요.
- **YouTube `invalid_grant`**: 리프레시 토큰이 만료되었습니다. 동의 화면이 *프로덕션*인지 확인하고 ③-4를 다시 하세요.
- **YouTube `quotaExceeded`**: 기본 할당량(10,000/일)이면 하루 업로드 약 6회까지 됩니다. 하루 1회면 충분합니다.
