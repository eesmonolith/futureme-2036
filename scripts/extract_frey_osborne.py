"""Extract Frey-Osborne 2013 Appendix A 702-occupation table from PDF.

Output: data/processed/frey_osborne_702.csv
Columns: rank, probability, label, soc_code, occupation
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "raw" / "frey_osborne_paper.pdf"
OUT = ROOT / "data" / "processed" / "frey_osborne_702.csv"

APPENDIX_START_PAGE = 56  # zero-indexed

# Match: <rank>.  <prob>  <label 0|1>  <SOC>  <occupation>
# Where occupation runs until next rank number "(NNN.) " or end.
ROW_RE = re.compile(
    r"(\d{1,3})\.\s+(\d\.\d{1,4})\s+(?:([01])\s+)?(\d{2}-\d{4})\s+(.+?)(?=\s+\d{1,3}\.\s+\d\.\d|\Z)",
    re.DOTALL,
)


HEADER_NOISE_RE = re.compile(
    r"(?:\d{2,3}\s+)?Computerisable\s+Rank\s+Probability\s+Label\s+SOC\s*code\s+Occupation",
    re.IGNORECASE,
)


def collect_text() -> str:
    reader = pypdf.PdfReader(str(PDF))
    chunks: list[str] = []
    for i in range(APPENDIX_START_PAGE, len(reader.pages)):
        chunks.append(reader.pages[i].extract_text() or "")
    raw = "\n".join(chunks)
    raw = HEADER_NOISE_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", raw)


def parse(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for m in ROW_RE.finditer(text):
        rank, prob, label, soc, occ = m.groups()
        if label is None:
            label = ""
        occ_clean = re.sub(r"\s+", " ", occ).strip().rstrip(",;.")
        # drop trailing page numbers like " 71" or " 72"
        occ_clean = re.sub(r"\s+\d{2,3}$", "", occ_clean)
        # fix ligature artifacts
        occ_clean = occ_clean.replace("ﬁ", "fi").replace("ﬂ", "fl")
        rows.append(
            {
                "rank": rank,
                "probability": prob,
                "label": label,
                "soc_code": soc,
                "occupation": occ_clean,
            }
        )
    return rows


def main() -> None:
    text = collect_text()
    rows = parse(text)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["rank", "probability", "label", "soc_code", "occupation"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} occupations to {OUT}")
    if rows:
        ranks = [int(r["rank"]) for r in rows]
        print(f"Rank min={min(ranks)} max={max(ranks)}")
        print("First 3:")
        for r in rows[:3]:
            print(" ", r)
        print("Last 3:")
        for r in rows[-3:]:
            print(" ", r)
        # quick coverage check
        expected = set(range(1, 703))
        got = set(ranks)
        missing = sorted(expected - got)
        dup = len(rows) - len(got)
        print(f"Missing ranks: {len(missing)} | duplicates: {dup}")
        if missing:
            print(" first 20 missing:", missing[:20])


if __name__ == "__main__":
    main()
