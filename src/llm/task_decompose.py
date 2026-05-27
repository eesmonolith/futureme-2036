"""Claude Haiku 4.5 task decomposition for Korean job descriptions.

Maps Korean job text → Frey-Osborne 5-task automation susceptibility scores.

Usage:
    python -m src.llm.task_decompose --precompute-all
    python -m src.llm.task_decompose --job "프로그래머"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PROC = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "data" / "cache" / "llm_tasks"
CALL_LOG = CACHE_DIR / "_call_log.jsonl"

MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are a labor-economics expert specialized in mapping Korean job descriptions to the Frey & Osborne (2013) automation-task framework.

Given a Korean job description, decompose the job into the following 5 canonical tasks and assign each an automation susceptibility score (0.0~1.0):

1. 요구사항 분석 (Requirement Analysis) — interpreting needs, ambiguous specs
2. 핵심 작업 수행 (Core Execution) — the central technical/manual work
3. 검증·테스트 (Verification & Testing) — quality control, validation
4. 배포·운영 (Deployment & Operation) — delivery, monitoring, maintenance
5. 문서·소통 (Documentation & Communication) — reporting, collaboration

Return STRICT JSON, no markdown, no commentary:
{
  "tasks": [
    {"name": "요구사항 분석", "score": 0.55, "rationale": "..."},
    {"name": "핵심 작업 수행", "score": 0.92, "rationale": "..."},
    {"name": "검증·테스트", "score": 0.88, "rationale": "..."},
    {"name": "배포·운영", "score": 0.42, "rationale": "..."},
    {"name": "문서·소통", "score": 0.35, "rationale": "..."}
  ],
  "weighted_risk": 0.62,
  "notes": "Korean-specific adjustment notes."
}

Rules:
- Calibrate against Frey & Osborne (2013) 702 occupations and OECD AI Exposure Index (2024).
- Rationale ≤ 2 sentences in Korean.
- weighted_risk = arithmetic mean of 5 task scores.
- Do NOT fabricate occupations not in the input.
- Output JSON only.
"""

USER_TEMPLATE = """직업명: {job_name}
KECO 코드: {keco_code}
한국직업사전 직무 설명:
{job_description}

위 직무를 5태스크로 분해하고 자동화 위험을 평가하라."""


def _load_anthropic():
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise SystemExit(
            "anthropic SDK not installed. Run: pip install anthropic"
        ) from e
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY missing. Set in .env or shell env."
        )
    return Anthropic()


def _prompt_hash() -> str:
    return "sha256:" + hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:16]


def _strip_json(text: str) -> str:
    """Defensively extract the first JSON object even if model wraps in fences."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in model output: {text[:200]}")
    return m.group(0)


def decompose(job_name: str, keco_code: str, job_description: str, client=None) -> dict:
    client = client or _load_anthropic()
    user_msg = USER_TEMPLATE.format(
        job_name=job_name, keco_code=keco_code, job_description=job_description
    )
    t0 = time.time()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    elapsed = time.time() - t0
    raw = resp.content[0].text
    parsed = json.loads(_strip_json(raw))

    payload = {
        "input": {
            "job_name": job_name,
            "keco_code": keco_code,
            "job_description": job_description,
            "source": "워크넷 KNOW + 한국직업사전 (요약)",
        },
        "model": MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system_prompt_hash": _prompt_hash(),
        "response": parsed,
        "usage": {
            "input_tokens": getattr(resp.usage, "input_tokens", None),
            "output_tokens": getattr(resp.usage, "output_tokens", None),
            "elapsed_seconds": round(elapsed, 2),
        },
    }
    return payload


def write_cache(keco_code: str, payload: dict) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out = CACHE_DIR / f"{keco_code}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with CALL_LOG.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "keco_code": keco_code,
                    "job_name": payload["input"]["job_name"],
                    "timestamp": payload["timestamp"],
                    "input_tokens": payload["usage"].get("input_tokens"),
                    "output_tokens": payload["usage"].get("output_tokens"),
                    "weighted_risk": payload["response"].get("weighted_risk"),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return out


def precompute_all(skip_existing: bool = True) -> None:
    targets = pd.read_csv(DATA_PROC / "target_50_jobs.csv")
    client = _load_anthropic()
    done = 0
    for _, row in targets.iterrows():
        keco = str(row["keco_code"])
        out = CACHE_DIR / f"{keco}.json"
        if skip_existing and out.exists():
            continue
        # MVP stub job description (until 한국직업사전 PDF parse lands)
        job_desc = (
            f"{row['job_name_kr']} (Frey-Osborne 매핑 SOC={row['soc_code']}, "
            f"기본 위험확률={row['frey_prob']}). "
            f"주요 직무 영역: {row['notes']}."
        )
        try:
            payload = decompose(row["job_name_kr"], keco, job_desc, client=client)
            write_cache(keco, payload)
            done += 1
            print(f"  ✓ {row['job_name_kr']} (KECO {keco}) → risk={payload['response']['weighted_risk']}")
        except Exception as e:
            print(f"  ✗ {row['job_name_kr']}: {e}", file=sys.stderr)
    print(f"Precomputed {done} jobs into {CACHE_DIR}")


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", help="single job name to decompose (debug)")
    parser.add_argument("--keco", help="KECO code (with --job)")
    parser.add_argument("--desc", help="job description (with --job)")
    parser.add_argument("--precompute-all", action="store_true")
    args = parser.parse_args()

    if args.precompute_all:
        precompute_all()
        return
    if args.job:
        payload = decompose(args.job, args.keco or "0000", args.desc or args.job)
        out = write_cache(args.keco or "debug", payload)
        print(f"Wrote {out}")
        print(json.dumps(payload["response"], ensure_ascii=False, indent=2))
        return
    parser.print_help()


if __name__ == "__main__":
    cli()
