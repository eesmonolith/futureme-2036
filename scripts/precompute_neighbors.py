"""Precompute safe adjacent jobs (Top-3, risk <= 0.3) for each target.

MVP stub: ranks neighbors by KECO major-category proximity + Claude risk gap.
Replace with SBERT cosine similarity + KEEP observed transition edges later.

Output: data/cache/neighbors/{KECO}.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_PROC = ROOT / "data" / "processed"
CACHE_NEIGH = ROOT / "data" / "cache" / "neighbors"
CACHE_LLM = ROOT / "data" / "cache" / "llm_tasks"

RISK_THRESHOLD = 0.30


def llm_risk(keco: str, fallback: float) -> float:
    f = CACHE_LLM / f"{keco}.json"
    if f.exists():
        return float(json.loads(f.read_text(encoding="utf-8"))["response"]["weighted_risk"])
    return fallback


EMERGING_CSV = DATA_PROC / "emerging_roles.csv"


def load_emerging() -> dict[str, list[dict]]:
    if not EMERGING_CSV.exists():
        return {}
    df = pd.read_csv(EMERGING_CSV)
    df["source_keco"] = df["source_keco"].astype(str)
    grouped: dict[str, list[dict]] = {}
    for keco, sub in df.groupby("source_keco"):
        grouped[keco] = [
            {
                "job_name": r["emerging_name"],
                "keco_code": "EMERGING",
                "risk": round(float(r["risk"]), 3),
                "category": "신생/인접 직업",
                "why": r["why"],
                "source": "emerging_roles.csv",
            }
            for _, r in sub.iterrows()
        ]
    return grouped


def main():
    CACHE_NEIGH.mkdir(parents=True, exist_ok=True)
    targets = pd.read_csv(DATA_PROC / "target_50_jobs.csv").copy()
    targets["keco_str"] = targets["keco_code"].astype(str)
    targets["risk"] = targets.apply(
        lambda r: llm_risk(str(r["keco_code"]), float(r["frey_prob"])), axis=1
    )
    emerging = load_emerging()

    written = 0
    seen: set[str] = set()
    for _, row in targets.iterrows():
        keco = row["keco_str"]
        if keco in seen:
            continue
        seen.add(keco)
        target_risk = row["risk"]
        target_cat = row["category"]

        # Same-category candidates with lower risk
        cand = targets[
            (targets["keco_str"] != keco)
            & (targets["risk"] < target_risk)
            & (targets["category"] == target_cat)
        ].copy()
        cand["risk_gap"] = target_risk - cand["risk"]
        cand = cand.sort_values("risk", ascending=True).head(3)

        neighbors: list[dict] = []
        for _, n in cand.iterrows():
            why = [f"동일 직군({target_cat}) 내 위험 감소 {(target_risk - n['risk']):.2f}"]
            if n["risk"] <= RISK_THRESHOLD:
                why.insert(0, "위험 ≤ 0.3 안전 영역")
            neighbors.append({
                "job_name": n["job_name_kr"],
                "keco_code": n["keco_str"],
                "risk": round(float(n["risk"]), 3),
                "category": n["category"],
                "why": " · ".join(why),
            })

        # Top up from emerging roles (curated KEEP-style transitions)
        e = emerging.get(keco, [])
        slots = 3 - len(neighbors)
        if slots > 0:
            neighbors.extend(e[:slots])

        # Last fallback: cross-category low risk
        if len(neighbors) < 3:
            extra = targets[
                (targets["keco_str"] != keco)
                & (~targets["keco_str"].isin([n["keco_code"] for n in neighbors]))
                & (targets["risk"] < target_risk)
            ].sort_values("risk").head(3 - len(neighbors))
            for _, n in extra.iterrows():
                neighbors.append({
                    "job_name": n["job_name_kr"],
                    "keco_code": n["keco_str"],
                    "risk": round(float(n["risk"]), 3),
                    "category": n["category"],
                    "why": f"인접 직군 안전 (위험 {n['risk']:.2f})",
                })

        payload = {
            "method": "stub-sbert + curated emerging roles (KEEP-style transitions)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_keco": keco,
            "target_job": row["job_name_kr"],
            "target_risk": round(float(target_risk), 3),
            "neighbors": neighbors[:3],
        }
        (CACHE_NEIGH / f"{keco}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        written += 1
    print(f"Wrote {written} neighbor lists to {CACHE_NEIGH}")


if __name__ == "__main__":
    main()
