"""Precompute demand+wage forecast 2026-2036 for 50 target jobs.

MVP stub: synthesizes Prophet-style curves from Frey-Osborne base risk +
Claude task-decomposition weighted risk. Each curve is annotated with
95% confidence band to support the 'scenario, not prediction' framing.

Replace with real Prophet fit when KEEP+GOMS sequence is loaded.

Output: data/cache/demand/{KECO}.json
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PROC = ROOT / "data" / "processed"
CACHE_DEMAND = ROOT / "data" / "cache" / "demand"
CACHE_LLM = ROOT / "data" / "cache" / "llm_tasks"

YEARS = list(range(2026, 2037))
BASE_JOBS = {
    # rough baseline 일자리 수 by category (단위: 명, 시연용 stub)
    "보건의료": 12000,
    "교육": 18000,
    "법률": 3000,
    "공공행정": 25000,
    "공공안전": 8000,
    "국방": 15000,
    "IT": 20000,
    "디자인": 7000,
    "공학": 14000,
    "과학": 5000,
    "경영금융": 22000,
    "예술방송": 6000,
    "예술체육": 4000,
    "서비스": 10000,
    "교통": 5500,
    "사회복지": 9000,
}
BASE_WAGE = {
    # 월평균 임금 (만원, 시연용 stub)
    "보건의료": 480,
    "교육": 360,
    "법률": 720,
    "공공행정": 350,
    "공공안전": 380,
    "국방": 400,
    "IT": 520,
    "디자인": 360,
    "공학": 480,
    "과학": 470,
    "경영금융": 500,
    "예술방송": 320,
    "예술체육": 380,
    "서비스": 280,
    "교통": 420,
    "사회복지": 300,
}


def get_llm_risk(keco: str, frey_prob: float) -> float:
    f = CACHE_LLM / f"{keco}.json"
    if f.exists():
        payload = json.loads(f.read_text(encoding="utf-8"))
        return float(payload["response"]["weighted_risk"])
    return float(frey_prob)


def build_curve(category: str, risk: float) -> dict:
    base_jobs = BASE_JOBS.get(category, 10000)
    base_wage = BASE_WAGE.get(category, 400)

    rows: list[dict] = []
    for i, y in enumerate(YEARS):
        t = i / (len(YEARS) - 1)
        # jobs decline scaled by risk; floor at 30% of baseline
        jobs_factor = max(0.3, 1 - risk * 0.6 * t)
        jobs = int(base_jobs * jobs_factor)
        # naive 95% CI band: widens with t
        band = jobs * 0.15 * (0.5 + t)
        jobs_lo = max(0, int(jobs - band))
        jobs_hi = int(jobs + band)

        # wage: nominal +2%/yr times automation discount (high-risk roles compress mid-tier wages)
        wage_growth = 1 + 0.02 * i
        wage_discount = 1 - 0.25 * risk * t
        wage = round(base_wage * wage_growth * wage_discount, 1)
        wage_band = wage * 0.12 * (0.5 + t)

        rows.append({
            "year": y,
            "jobs": jobs,
            "jobs_lo": jobs_lo,
            "jobs_hi": jobs_hi,
            "wage_won_man": wage,
            "wage_lo": round(wage - wage_band, 1),
            "wage_hi": round(wage + wage_band, 1),
        })

    return {
        "method": "stub-prophet (frey-osborne + claude risk weighted)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "risk_input": risk,
        "forecast": rows,
        "ethical_note": "예측 아닌 시나리오. 95% 신뢰구간 음영 표시 권장.",
    }


def main():
    CACHE_DEMAND.mkdir(parents=True, exist_ok=True)
    targets = pd.read_csv(DATA_PROC / "target_50_jobs.csv")
    seen: set[str] = set()
    written = 0
    for _, row in targets.iterrows():
        keco = str(row["keco_code"])
        if keco in seen:
            continue
        seen.add(keco)
        risk = get_llm_risk(keco, float(row["frey_prob"]))
        payload = build_curve(str(row["category"]), risk)
        payload["job_name"] = row["job_name_kr"]
        payload["keco_code"] = keco
        out = CACHE_DEMAND / f"{keco}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written += 1
    print(f"Wrote {written} demand forecasts to {CACHE_DEMAND}")


if __name__ == "__main__":
    main()
