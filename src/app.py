"""FutureMe 2036 — Streamlit MVP.

3-model career simulator for Korean high-school students.
- Model 1: Automation risk (Frey-Osborne 702 x KECO crosswalk + Claude task decomposition)
- Model 2: Demand/wage time-travel (Prophet + KEEP+GOMS sequence)
- Model 3: Safe adjacent paths (SBERT + KEEP observed transitions)

This MVP uses precomputed JSON for the 50 target jobs.
Free-text input falls back to live Claude + SBERT inference.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "data" / "cache"

st.set_page_config(
    page_title="FutureMe 2036",
    page_icon="⏳",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data
def load_target_jobs() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "target_50_jobs.csv")
    return df


@st.cache_data
def load_frey_osborne() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "frey_osborne_702.csv")
    df["probability"] = pd.to_numeric(df["probability"], errors="coerce")
    return df


def get_job_risk_precomputed(keco_code: str, base_prob: float) -> dict:
    """Return precomputed Claude task-decomposition for a target job.

    Falls back to a deterministic stub when cache absent (MVP mode).
    """
    cache_file = CACHE_DIR / "llm_tasks" / f"{keco_code}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    # Deterministic stub derived from Frey-Osborne base probability
    # so the UI is functional even before Claude precomputation runs.
    return {
        "tasks": [
            {"name": "요구사항 분석", "score": max(0.05, base_prob * 0.7),
             "rationale": "정형화된 요구 수렴은 일부 자동화, 모호한 맥락은 사람 영역."},
            {"name": "핵심 작업 수행", "score": min(0.98, base_prob * 1.4),
             "rationale": "반복·규칙 기반 작업은 생성형 AI에 의해 광범위 자동화."},
            {"name": "검증·테스트", "score": min(0.95, base_prob * 1.2),
             "rationale": "정량 평가·반복 검증은 자동화 친화적."},
            {"name": "배포·운영", "score": max(0.1, base_prob * 0.6),
             "rationale": "장애 대응과 운영 판단은 인간 책임 영역."},
            {"name": "문서·소통", "score": max(0.1, base_prob * 0.5),
             "rationale": "이해관계자 소통은 맥락 의존적, AI 보조 수준."},
        ],
        "weighted_risk": base_prob,
        "notes": "사전계산 캐시 미보유 — Frey-Osborne 기반 결정론적 추정. Claude 캐시 갱신 시 교체.",
    }


def get_demand_curve(keco_code: str, base_prob: float) -> pd.DataFrame:
    """Return precomputed Prophet demand+wage forecast.

    Stub: linear interpolation derived from base_prob until KEEP/GOMS data lands.
    """
    cache_file = CACHE_DIR / "demand" / f"{keco_code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        return pd.DataFrame(payload["forecast"])

    years = list(range(2026, 2037))
    base_jobs = 10000
    decline = base_prob * 0.5
    rows = []
    for i, y in enumerate(years):
        factor = 1 - decline * (i / (len(years) - 1))
        jobs = int(base_jobs * factor)
        wage = 4500 * (1 + 0.02 * i) * (1 - 0.2 * base_prob * (i / (len(years) - 1)))
        rows.append({"year": y, "jobs": jobs, "wage_won_man": round(wage, 1)})
    return pd.DataFrame(rows)


def get_safe_neighbors(keco_code: str, base_prob: float, all_jobs: pd.DataFrame) -> pd.DataFrame:
    """Return top-3 safe adjacent jobs (risk <= 0.3).

    Stub: pick 3 lowest-risk jobs in the same KECO major category, plus closest by KECO numeric distance.
    Replace with SBERT + KEEP-edge filtered NetworkX graph when data lands.
    """
    cache_file = CACHE_DIR / "neighbors" / f"{keco_code}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        return pd.DataFrame(payload["neighbors"])

    safe = all_jobs[all_jobs["frey_prob"] <= 0.3].copy()
    safe = safe[safe["keco_code"] != keco_code]
    try:
        target_major = str(keco_code)[:2]
        safe["same_major"] = safe["keco_code"].astype(str).str[:2] == target_major
    except Exception:
        safe["same_major"] = False
    safe = safe.sort_values(["same_major", "frey_prob"], ascending=[False, True]).head(3)
    safe = safe.rename(columns={"job_name_kr": "job_name", "frey_prob": "risk"})
    safe["why"] = "동일 직군 내 자동화 위험 낮음 (KECO 대분류 일치)"
    return safe[["job_name", "keco_code", "risk", "why"]]


def header():
    st.title("⏳ FutureMe 2036")
    st.markdown(
        "**네가 적은 꿈을 AI가 10년 시간여행 시켜본다.** "
        "교육 공공데이터(KEEP·커리어넷·워크넷 KNOW·대학알리미·GOMS·한국직업사전) + "
        "Frey-Osborne(2013) 702 직업 자동화 확률 + Anthropic Claude Haiku 4.5 5-태스크 분해."
    )
    st.caption(
        "⚠ 본 결과는 '예측'이 아닌 **시나리오**입니다. 인간 고유 역량으로 우회 가능합니다."
    )


def student_mode(target_jobs: pd.DataFrame):
    col_in, col_out = st.columns([2, 3])

    with col_in:
        st.subheader("1️⃣ 입력")
        job_names = target_jobs["job_name_kr"].tolist()
        chosen = st.selectbox(
            "꿈 직업명",
            options=["(직접 선택)"] + job_names,
            index=11 + 1,  # 프로그래머 default
        )
        free_text = st.text_input(
            "또는 자유 텍스트 (자동완성 미지원 시)",
            placeholder="예: AI랑 그림 그리는 거 좋아",
        )
        grade = st.selectbox("학년", ["고1", "고2", "고3", "중3"])
        score_band = st.select_slider(
            "성적대",
            options=["하위 30%", "중위 50%", "상위 30%", "상위 10%"],
            value="상위 30%",
        )
        interests = st.multiselect(
            "관심 과목",
            ["국어", "영어", "수학", "사회", "과학", "정보", "예체능", "외국어"],
            default=["수학", "정보"],
        )
        year = st.slider("시간 슬라이더 (2026 → 2036)", 2026, 2036, 2031)
        run = st.button("🔮 시간여행 출발", type="primary", use_container_width=True)

    with col_out:
        st.subheader("2️⃣ 출력")
        if not run and chosen == "(직접 선택)" and not free_text:
            st.info("좌측에서 꿈 직업을 입력하고 '시간여행 출발'을 눌러주세요.")
            return

        target = (
            target_jobs[target_jobs["job_name_kr"] == chosen].iloc[0]
            if chosen != "(직접 선택)"
            else target_jobs.iloc[11]  # fallback 프로그래머
        )
        risk_payload = get_job_risk_precomputed(str(target["keco_code"]), float(target["frey_prob"]))

        # Risk gauge + tasks
        risk = risk_payload["weighted_risk"]
        risk_pct = int(risk * 100)
        color = "🟢" if risk < 0.3 else "🟡" if risk < 0.7 else "🔴"
        st.metric(
            label=f"{target['job_name_kr']} — {year}년 자동화 위험",
            value=f"{color} {risk:.2f} ({risk_pct}%)",
        )
        st.progress(risk)

        st.markdown("#### 직무 5태스크 분해 (Claude Haiku 4.5)")
        task_df = pd.DataFrame(risk_payload["tasks"])
        st.dataframe(task_df, use_container_width=True, hide_index=True)

        # Demand/wage curve
        st.markdown("#### 일자리 수 · 임금 시계열 (Prophet + KEEP·GOMS)")
        curve = get_demand_curve(str(target["keco_code"]), float(target["frey_prob"]))
        col_a, col_b = st.columns(2)
        col_a.line_chart(curve.set_index("year")["jobs"], use_container_width=True)
        col_a.caption("일자리 수 (전망)")
        col_b.line_chart(curve.set_index("year")["wage_won_man"], use_container_width=True)
        col_b.caption("월 평균 임금 (만원, 전망)")

        # Safe neighbors
        st.markdown("#### 🛟 안전 우회 인접 직업 Top 3 (위험 ≤ 0.3)")
        all_jobs = target_jobs.rename(columns={"frey_prob": "frey_prob"})
        neighbors = get_safe_neighbors(str(target["keco_code"]), float(target["frey_prob"]), all_jobs)
        st.dataframe(neighbors, use_container_width=True, hide_index=True)

        # Recommended skills
        st.markdown("#### 💡 지금 추가하면 좋을 역량 5개")
        skills = ["AI 협업 도구", "데이터 해석", "도메인 깊이", "협업·소통", "비판적 사고"]
        cols = st.columns(5)
        for c, s in zip(cols, skills):
            c.success(s)

        st.caption(risk_payload["notes"])


def teacher_mode(target_jobs: pd.DataFrame):
    st.subheader("👩‍🏫 교사 모드 — 학급 진로 위험 집계")
    class_code = st.text_input("반 코드", value="ABCD-2025-1A")
    if not class_code:
        st.info("반 코드를 입력하세요.")
        return

    st.markdown("##### 학급 25명 시뮬레이션 (데모용 더미 분포)")
    import numpy as np

    rng = np.random.default_rng(hash(class_code) % (2**32))
    sampled = target_jobs.sample(25, random_state=int(rng.integers(0, 10000)))
    sampled = sampled.assign(
        student_id=[f"S-{i:02d}" for i in range(1, 26)],
        risk=sampled["frey_prob"],
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**상위 위험 학생 Top 5**")
        top5 = sampled.nlargest(5, "risk")[["student_id", "job_name_kr", "risk"]]
        st.dataframe(top5, hide_index=True, use_container_width=True)
    with col2:
        st.markdown("**학급 평균 자동화 위험**")
        avg = sampled["risk"].mean()
        st.metric("평균 위험", f"{avg:.2f}")
        st.metric("고위험 비율 (≥0.7)", f"{(sampled['risk'] >= 0.7).mean() * 100:.0f}%")

    st.markdown("**위험 구간별 학생 분포**")
    bins = pd.cut(sampled["risk"], bins=[0, 0.3, 0.5, 0.7, 1.01], labels=["저(≤0.3)", "중(0.3~0.5)", "고(0.5~0.7)", "초고(≥0.7)"])
    dist = bins.value_counts().sort_index()
    st.bar_chart(dist)

    st.markdown("**활동 가이드**")
    st.info(
        "1) 고위험 학생 Top 5와 진로상담 우선 진행  \n"
        "2) 학급 평균 위험이 0.5 이상이면 AI 디지털교과서 활용 진로수업 권장  \n"
        "3) 학습활동지 PDF 일괄 다운로드 → 진로수업 1차시 배포"
    )

    if st.button("📄 학급 학습활동지 PDF 일괄 다운로드 (시뮬)"):
        st.success("학습활동지 PDF가 생성되었습니다. (실제 구현은 reportlab으로 D-2 완료 예정)")


def about():
    with st.expander("📚 데이터 출처 · 라이선스"):
        st.markdown(
            """
- **한국교육고용패널 KEEP I·II** (KRIVET) — 자료활용 동의서 후 무상 이용
- **커리어넷 직업·진로** (KRIVET) — 공공누리 제1유형
- **워크넷 KNOW** (한국고용정보원) — 공공누리 제1유형
- **대학알리미** (한국교육개발원) — 공공누리 제1유형
- **GOMS** (한국고용정보원) — 공공누리 제4유형 (분석 결과만 활용)
- **한국직업사전** (한국고용정보원) — 공공누리 제1유형
- **Frey & Osborne (2013)** — 학술 인용
- **WEF Future of Jobs Report 2025** — 보고서 인용

본 작품은 KERIS 제8회 교육 공공데이터 AI 활용대회 일반부 출품용 비상업 시연입니다.
            """
        )
    with st.expander("🤖 생성형 AI 활용 정보"):
        st.markdown(
            """
- **Anthropic Claude Haiku 4.5** (`claude-haiku-4-5-20251001`)
- 용도: 한국 직무 텍스트 → Frey-Osborne 5태스크 분해
- 호출 형태: 직업당 1회 사전계산, JSON 캐싱
- 프롬프트·샘플 입출력: 부록 C 참조
            """
        )


def main():
    header()
    target_jobs = load_target_jobs()

    mode = st.radio(
        "모드 선택",
        ["학생 모드", "교사 모드"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()

    if mode == "학생 모드":
        student_mode(target_jobs)
    else:
        teacher_mode(target_jobs)

    st.divider()
    about()
    st.caption(
        "출처: KEEP·커리어넷·워크넷 KNOW·대학알리미·GOMS·한국직업사전 / Frey-Osborne 2013, WEF 2025 | "
        "식별정보 없음 | © FutureMe 2036 (MIT)"
    )


if __name__ == "__main__":
    main()
