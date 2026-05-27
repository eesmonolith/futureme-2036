# FutureMe 2036

> AI가 네 꿈을 10년 시간여행 시켜준다.

제8회 KERIS 교육 공공데이터 AI 활용대회 일반부 출품작.

## 개요

고교생이 꿈 직업을 입력하면 2026~2036년 동안의 ① 자동화 위험 ② 수요·임금 변화 ③ 안전 인접 직업 우회 경로를 한 화면에 시각화한다.

## 기술 스택

- **Backend**: FastAPI + Python 3.11
- **Frontend**: Next.js 14 + React + Tailwind + Recharts + react-force-graph-2d
- **ML**: Prophet, sentence-transformers (`jhgan/ko-sroberta-multitask`), NetworkX, scikit-learn
- **LLM**: Anthropic Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) — 사전처리 1회, 결과 JSON 캐싱
- **PDF**: reportlab (학습활동지)
- **배포**: Netlify (프론트) + Render free tier (백엔드)

## 3가지 AI 모델

| 모델 | 입력 | 방법 | 출력 |
|---|---|---|---|
| ① 자동화 위험 | KNOW 직무 텍스트 | Frey-Osborne 702 × KECO 크로스워크 + Claude 5태스크 분해 | 한국형 위험점수 |
| ② 수요·임금 예측 | GOMS 2014~2023 시계열 | Prophet 외삽 + WEF 2025 라벨 보정 | 2036 일자리수·임금 곡선 |
| ③ 안전 우회 경로 | 직무 SBERT 임베딩 | NetworkX 코사인 유사도 그래프 | 위험 ≤ 0.3 인접 직업 최단 경로 |

## 공공데이터 5종 (출처)

- 한국직업능력연구원 **커리어넷** 직업·진로 정보 (공공누리 제1유형)
- 한국고용정보원 **워크넷 KNOW** 직업정보 (공공누리 제1유형)
- 한국교육개발원 **대학알리미** 학과정보·취업률 (공공누리 제1유형)
- 한국고용정보원 **GOMS** 대졸자직업이동경로조사 (공공누리 제4유형, 분석 결과만 활용)
- 한국고용정보원 **한국직업사전** (공공누리 제1유형)

**외부 보강**
- Frey, C. B., & Osborne, M. A. (2013). *The Future of Employment.* Oxford WP.
- World Economic Forum (2025). *Future of Jobs Report.*

데이터 다운로드 일자: 2026-05-28

## 디렉토리

```
prototype/
├── README.md
├── MODEL_CARD.md          # 모델별 학습·검증·한계
├── LICENSE                # MIT
├── requirements.txt
├── .env.example
├── data/
│   ├── raw/               # 다운받은 원본 (gitignore)
│   ├── processed/         # 정제된 CSV/JSON (커밋)
│   └── cache/             # 모델 출력 캐시 (gitignore)
├── src/
│   ├── main.py            # FastAPI 진입점
│   ├── data_pipeline.py   # 공공데이터 전처리
│   ├── models/
│   │   ├── automation_risk.py
│   │   ├── demand_forecast.py
│   │   └── safe_path.py
│   ├── llm/
│   │   └── task_decompose.py  # Claude 5태스크 분해
│   ├── teacher.py         # 교사 모드 집계
│   └── worksheet.py       # 학습활동지 PDF 생성
├── scripts/
│   ├── download_data.py   # 데이터 다운로드 자동화
│   ├── precompute_50.py   # 50개 직업 사전계산
│   └── reproduce.ipynb    # Colab 재현 노트북
├── notebooks/             # EDA
└── frontend/              # Next.js
```

## 실행

```bash
# 1. 환경
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # ANTHROPIC_API_KEY 입력

# 2. 데이터 다운로드 (수동: docs/data-download-guide.md 참조)

# 3. 사전계산
python scripts/precompute_50.py

# 4. 백엔드
uvicorn src.main:app --reload

# 5. 프론트
cd frontend && npm install && npm run dev
```

## 라이선스

MIT (소스코드). 공공데이터는 각 출처의 공공누리 라이선스를 따른다.
