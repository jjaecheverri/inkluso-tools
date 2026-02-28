# HumanKlu™ — Human Calibration Standard for AI-Generated Intelligence
### HumanKlu Calibration Protocol · HKP v1.1

---

## Overview

HumanKlu is a deterministic artifact pipeline that evaluates AI-generated intelligence
against a structured calibration protocol and produces tamper-evident, auditable output.

**No external dependencies. Pure Python 3.11+. Runs in under 2 seconds per report.**

---

## Deliverable Artifacts

| Artifact | Description |
|---|---|
| `report.html` | Structured intelligence article with embedded SCI badge |
| `evidence.json` | Claim-level evidence log (VERIFIED vs INFERRED) + `claim_flags` |
| `sci_score.json` | Signal Confidence Index with `evid_raw`, `evid_effective`, `certification_level` |
| `humanklu_audit.json` | Tamper-evident audit record (`hkp_version: "1.1"`) |
| `ledger.jsonl` | Append-only reputation ledger (hash-chained entries) |

---

## HKP v1.1 Scoring Protocol

### Dimensions (0–10)

| Code | Dimension |
|---|---|
| EVID | Evidence Integrity |
| MECH | Mechanism Clarity |
| INC | Incentive Decode |
| RISK | Risk Realism |
| SPEC | Specificity |

### HCI Formula

```
inferred_ratio = count(INFERRED claims) / total_claims
                 [defaults to 1.0 if no claims]

EVID_effective = EVID_raw
  if inferred_ratio > 0.75 → EVID_effective = min(EVID_raw, 6.5)
  if inferred_ratio > 0.60 → EVID_effective = min(EVID_raw, 7.2)

HCI = average(EVID_effective, MECH, INC, RISK, SPEC)
```

### Certification Levels (highest-to-lowest priority)

| Level | HCI | EVID_eff | inferred_ratio | SPEC | Constraints |
|---|---|---|---|---|---|
| 🏛 HK-INSTITUTIONAL | ≥ 8.5 | ≥ 8.2 | ≤ 0.40 | ≥ 7.5 | no hallucination, no ABSENCE_ASSERTION, `institutional_requires_two_reviews: true` |
| ⭐ HK-PRO | ≥ 7.8 | ≥ 7.6 | ≤ 0.50 | ≥ 7.0 | no ABSENCE_ASSERTION, `pro_requires_second_review: true` |
| ✅ HK-VERIFIED | ≥ 7.3 | ≥ 7.2 | ≤ 0.60 | ≥ 6.5 | no ABSENCE_ASSERTION |
| 🔍 HK-REVIEWED | ≥ 6.0 | ≥ 6.0 | — | — | default if thresholds not met |
| ❌ HK-REJECTED | — | — | — | — | hallucination OR EVID_eff < 6 OR HCI < 5.5 |

### Absence Assertion Detection

Claims trigger `ABSENCE_ASSERTION` flag when:
- Text contains one of: `"no third-party audit"`, `"no audit"`, `"no evidence found"`, `"no public audit"`
- **AND** `source.uri` is null

Flagged claims block HK-VERIFIED / HK-PRO / HK-INSTITUTIONAL certification.

---

## Folder Structure

```
humanklu/
├── scripts/
│   ├── pipeline.py          # Single-report pipeline (HKP v1.1)
│   └── batch_run.py         # Batch runner
├── schemas/
│   └── schemas.json         # Consolidated JSON Schema (all 5 artifacts)
├── inputs/                  # Input JSON files for batch runs
│   ├── 01_rejected.json
│   ├── 02_reviewed.json
│   ├── 03_verified.json
│   ├── 04_pro.json
│   └── 05_institutional.json
├── batch_run/
│   ├── runs/
│   │   └── <run_id>/        # Per-run output (5 artifacts)
│   ├── summary.json
│   └── summary.csv
├── runs/                    # Ad-hoc single runs
├── ledger.jsonl             # Append-only global ledger
└── README.md
```

---

## Running Locally

### Requirements
- Python 3.11+ (stdlib only)

### Single Report
```bash
python scripts/pipeline.py \
  --input inputs/03_verified.json \
  --output runs/my_run_001

# Optional deterministic ID:
python scripts/pipeline.py \
  --input inputs/03_verified.json \
  --output runs/my_run_001 \
  --run-id HK-2026-MYTEST
```

### Batch Run
```bash
python scripts/batch_run.py \
  --inputs ./inputs \
  --output ./batch_run
```

Produces:
- `batch_run/runs/<input_stem>/` — full artifact set per input
- `batch_run/summary.json` — aggregate metrics + run list
- `batch_run/summary.csv`  — spreadsheet-friendly version

---

## Input Schema (report_input)

```json
{
  "title":   "Your Report Title",
  "topic":   "Domain / Sector",
  "summary": "Executive summary paragraph.",
  "author":  { "model_version": "gpt-4o", "organization": "Your Org" },
  "dimensions": {
    "EVID": { "score": 7.5, "rationale": "..." },
    "MECH": { "score": 7.2, "rationale": "..." },
    "INC":  { "score": 7.0, "rationale": "..." },
    "RISK": { "score": 7.1, "rationale": "..." },
    "SPEC": { "score": 6.9, "rationale": "..." }
  },
  "hallucination_flags": [],
  "claims": [
    {
      "text": "Claim text here.",
      "evidence_type": "VERIFIED",
      "source": {
        "type": "JOURNAL",
        "uri":  "https://example.com/paper",
        "title": "Paper Title"
      }
    },
    {
      "text": "Inferred claim without source.",
      "evidence_type": "INFERRED"
    }
  ]
}
```

---

## HKP v1.1 Changelog (vs v2.0)

| Change | Detail |
|---|---|
| `inferred_ratio` default | Returns `1.0` when claim list is empty (was `0.0`) |
| Per-claim flags | `claim_flags[]` on each evidence entry (was global only) |
| `inferred_ratio` in evidence | Added at evidence.json root |
| EVID storage | `evid_raw` + `evid_effective` stored separately; `dims` dict NOT mutated |
| HCI uses `evid_effective` | Effective EVID drives HCI computation |
| Stricter cert thresholds | HK-VERIFIED: HCI 7.3/EVID 7.2/SPEC 6.5; HK-PRO: HCI 7.8/EVID 7.6/SPEC 7.0; HK-INSTITUTIONAL: HCI 8.5/EVID 8.2/SPEC 7.5 |
| HK-REJECTED first-class | Explicit cert level (was `NOT-CERTIFIED`) |
| Reviewer flags | `pro_requires_second_review`, `institutional_requires_two_reviews` |
| Audit `hkp_version` | Field `"1.1"` added to humanklu_audit.json |
| Ledger `evid_effective` | Stored in ledger entry (replaces `verdict`) |
| Absence phrases | Refined to 4 specific phrases per spec |

---

© 2026 HumanKlu™ — HKP v1.1
