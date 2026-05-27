# 배포 가이드 — Streamlit Community Cloud (무료)

## 1. GitHub 레포 생성
1. https://github.com/new → repo name: `futureme-2036` (Public)
2. 로컬에서:
   ```bash
   cd prototype
   git remote add origin https://github.com/<YOUR_USERNAME>/futureme-2036.git
   git add .
   git commit -m "Initial commit: FutureMe 2036 MVP"
   git push -u origin main
   ```

## 2. Streamlit Cloud 배포
1. https://share.streamlit.io 접속 → GitHub 로그인
2. "New app" → 레포 선택 `futureme-2036`
3. Branch: `main`, Main file path: `src/app.py`
4. Advanced settings → Secrets:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Deploy → URL: `https://futureme-2036.streamlit.app` (또는 사용자명 포함)

## 3. 도메인 변경 시
기획서 PDF p.3·9·15·README의 URL을 실제 발급 URL로 일괄 치환:
```bash
grep -rl "futureme-2036.netlify.app" ../proposal ../prototype \
  | xargs sed -i '' 's|futureme-2036.netlify.app|<실제 URL>|g'
```

## 4. 제출 사이트 등록 시 URL
- 공모 운영안내 §4 "온라인(웹·앱) 구축된 경우 URL 포함 제출"
- 제출 페이지에 위 URL 그대로 입력
