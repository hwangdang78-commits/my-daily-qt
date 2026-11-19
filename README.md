# 생명의 삶 매일 QT — 완전 자동 업데이트 앱 배포 가이드

이 패키지를 **GitHub(무료)**에 한 번만 올려두면, **매일 새벽 00:05(한국시간)**에 자동으로 두란노 오늘의 QT 본문을 가져오고, 설정하신 **10단계 해설 + 4가지 모드(개인 묵상용·소그룹 나눔용·설교용·순장예배 QT 나눔용)** JSON을 생성해 내 휴대폰/PC 웹 앱에 자동 반영합니다.

---

## 5분 설정 순서

### 1단계: 무료 Gemini API 키 발급
1. [Google AI Studio](https://aistudio.google.com/app/apikey)에 접속해 로그인합니다.
2. **Create API key** 버튼을 눌러 API 키를 복사해 둡니다.

### 2단계: GitHub 저장소 생성 및 파일 업로드
1. [GitHub](https://github.com/new)에서 새 저장소(예: `my-daily-qt`)를 **Public**으로 만듭니다.
2. 이 ZIP 파일의 압축을 푼 뒤, 폴더 안의 모든 파일(`index.html`, `requirements.txt`, `README.md`, `scripts/`, `.github/`)을 저장소에 업로드(Commit)합니다.

### 3단계: API 키 등록 (GitHub Secrets)
1. 만든 GitHub 저장소 상단의 **Settings → Secrets and variables → Actions**로 이동합니다.
2. **New repository secret** 버튼을 클릭합니다.
   - **Name**: `GEMINI_API_KEY`
   - **Secret**: 1단계에서 복사한 Gemini API 키 붙여넣기
3. 저장합니다.

### 4단계: 무료 웹 주소 켜기 (GitHub Pages)
1. 저장소 상단의 **Settings → Pages**로 이동합니다.
2. **Source**를 `Deploy from a branch`, **Branch**를 `main` / `/ (root)`로 선택하고 **Save**를 누릅니다.
3. 1~2분 뒤 `https://<내아이디>.github.io/my-daily-qt/` 주소로 나만의 매일 QT 앱이 열립니다!
   - 앱은 HTTPS 주소에서 열리면 자동으로 같은 저장소의 `./qt/{date}.json` 피드를 인식해 매일 최신 말씀과 10단계 해설을 불러옵니다.

### 5단계: 첫 수동 테스트 & 휴대폰 홈 화면에 추가
1. 저장소 상단의 **Actions → Daily QT Auto-Sync (00:05 KST) → Run workflow**를 한 번 눌러 오늘자 JSON이 `qt/` 폴더에 자동 생성되는지 확인합니다.
2. 휴대폰 브라우저(사파리/크롬)로 내 GitHub Pages 주소를 연 뒤 **'홈 화면에 추가'**를 누르면 매일 아침 일반 앱처럼 바로 열어 묵상하실 수 있습니다.
