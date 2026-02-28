#!/usr/bin/env python3
"""
HumanKlu™ Artifact Pipeline
Human Calibration Standard for AI-Generated Intelligence
HumanKlu Calibration Protocol — HKP v1.1

Changes in v1.1 vs v2.0:
  - inferred_ratio defaults to 1.0 when claim list is empty
  - Per-claim claim_flags[] in evidence.json entries
  - inferred_ratio stored at evidence.json root
  - EVID stored as evid_raw + evid_effective (dims dict is NOT mutated)
  - HCI computed from evid_effective
  - Stricter cert-level thresholds (see determine_certification_level)
  - HK-REJECTED is now a first-class cert level
  - pro_requires_second_review / institutional_requires_two_reviews fields
  - humanklu_audit.json gets hkp_version, evid_raw, evid_effective, flags[]
  - Ledger entry stores evid_effective
  - Consolidated schemas/schemas.json (produced separately)

Usage:
    python pipeline.py --input input.json --output ./runs/run_001 [--run-id HK-2026-XXXX]
"""

import argparse
import hashlib
import json
import os
import random
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_VERSION = "HKP-1.1"

# ─────────────────────────────────────────────────────────────────
# CERT META  — badge colours per v1.1 spec
# ─────────────────────────────────────────────────────────────────
CERT_META = {
    "HK-INSTITUTIONAL": {
        "bg":      "#1A1200",
        "border":  "#D4AF37",
        "text":    "#D4AF37",
        "icon":    "🏛",
        "label":   "HK-INSTITUTIONAL",
    },
    "HK-PRO": {
        "bg":      "#0D2010",
        "border":  "#D4AF37",
        "text":    "#34D399",
        "icon":    "⭐",
        "label":   "HK-PRO",
    },
    "HK-VERIFIED": {
        "bg":      "#0D2010",
        "border":  "#34D399",
        "text":    "#34D399",
        "icon":    "✅",
        "label":   "HK-VERIFIED",
    },
    "HK-REVIEWED": {
        "bg":      "#1A1500",
        "border":  "#FBBF24",
        "text":    "#FBBF24",
        "icon":    "🔍",
        "label":   "HK-REVIEWED",
    },
    "HK-REJECTED": {
        "bg":      "#1A0A0A",
        "border":  "#F87171",
        "text":    "#F87171",
        "icon":    "❌",
        "label":   "HK-REJECTED",
    },
}

# ─────────────────────────────────────────────────────────────────
# ABSENCE ASSERTION PHRASES  (v1.1)
# ─────────────────────────────────────────────────────────────────
ABSENCE_PHRASES = [
    "no third-party audit",
    "no audit",
    "no evidence found",
    "no public audit",
]


# ─────────────────────────────────────────────────────────────────
# INFERRED RATIO
# ─────────────────────────────────────────────────────────────────
def compute_inferred_ratio(claims: list) -> float:
    """Fraction of claims with evidence_type == 'INFERRED'.
    Returns 1.0 if claims list is empty (conservative default)."""
    if not claims:
        return 1.0
    inferred = sum(1 for c in claims if c.get("evidence_type", "INFERRED") == "INFERRED")
    return round(inferred / len(claims), 4)


# ─────────────────────────────────────────────────────────────────
# EVID CEILING
# ─────────────────────────────────────────────────────────────────
def apply_evid_ceiling(evid_raw: float, inferred_ratio: float) -> tuple:
    """Returns (evid_effective, ceiling_note | None).
    Stores both values; original dims dict is NOT mutated."""
    if inferred_ratio > 0.75:
        cap  = 6.5
        note = f"EVID capped at {cap} (inferred_ratio={inferred_ratio:.4f} > 0.75)"
        return min(evid_raw, cap), note
    if inferred_ratio > 0.60:
        cap  = 7.2
        note = f"EVID capped at {cap} (inferred_ratio={inferred_ratio:.4f} > 0.60)"
        return min(evid_raw, cap), note
    return evid_raw, None


# ─────────────────────────────────────────────────────────────────
# ABSENCE ASSERTION DETECTION
# ─────────────────────────────────────────────────────────────────
def detect_absence_assertions(claims: list) -> list:
    """Returns list of flag dicts for claims that trigger ABSENCE_ASSERTION.
    Condition: claim text contains an absence phrase AND source URI is null."""
    flagged = []
    for c in claims:
        text_lower = c.get("text", "").lower()
        matched    = next((p for p in ABSENCE_PHRASES if p in text_lower), None)
        if not matched:
            continue
        source = c.get("source") or {}
        uri    = source.get("uri") or c.get("source_url")
        if not uri:
            flagged.append({
                "claim_id":      c.get("claim_id", "?"),
                "flag_type":     "ABSENCE_ASSERTION",
                "matched_phrase": matched,
                "detail":        "Claim asserts absence of evidence but provides no source URI.",
            })
    return flagged


# ─────────────────────────────────────────────────────────────────
# HCI  (uses evid_effective, not dims["EVID"]["score"])
# ─────────────────────────────────────────────────────────────────
def compute_hci(dims: dict, evid_effective: float) -> float:
    """HCI = average(EVID_effective, MECH, INC, RISK, SPEC)."""
    scores = [
        evid_effective,
        dims["MECH"]["score"],
        dims["INC"]["score"],
        dims["RISK"]["score"],
        dims["SPEC"]["score"],
    ]
    return round(sum(scores) / len(scores), 2)


# ─────────────────────────────────────────────────────────────────
# CERTIFICATION LEVEL  (HKP v1.1 — evaluated highest-to-lowest)
# ─────────────────────────────────────────────────────────────────
def determine_certification_level(
    dims: dict,
    evid_effective: float,
    hci: float,
    inferred_ratio: float,
    hallucination_flags: list,
    has_absence_assertions: bool,
) -> tuple:
    """Returns (certification_level, extra_fields dict)."""
    spec = dims["SPEC"]["score"]

    # HK-REJECTED gate — evaluated first
    if hallucination_flags or evid_effective < 6.0 or hci < 5.5:
        return "HK-REJECTED", {}

    # HK-INSTITUTIONAL
    if (
        hci             >= 8.5
        and evid_effective  >= 8.2
        and inferred_ratio  <= 0.40
        and spec            >= 7.5
        and not has_absence_assertions
        and not hallucination_flags
    ):
        return "HK-INSTITUTIONAL", {"institutional_requires_two_reviews": True}

    # HK-PRO
    if (
        hci             >= 7.8
        and evid_effective  >= 7.6
        and inferred_ratio  <= 0.50
        and spec            >= 7.0
        and not has_absence_assertions
    ):
        return "HK-PRO", {"pro_requires_second_review": True}

    # HK-VERIFIED
    if (
        hci             >= 7.3
        and evid_effective  >= 7.2
        and inferred_ratio  <= 0.60
        and spec            >= 6.5
        and not has_absence_assertions
    ):
        return "HK-VERIFIED", {}

    # HK-REVIEWED  (minimum gate: HCI>=6.0, EVID_eff>=6.0 — else REJECTED)
    if hci >= 6.0 and evid_effective >= 6.0:
        return "HK-REVIEWED", {}

    return "HK-REJECTED", {}


# ─────────────────────────────────────────────────────────────────
# ID GENERATORS
# ─────────────────────────────────────────────────────────────────
def _rand(k: int, chars: str = string.ascii_uppercase + string.digits) -> str:
    return "".join(random.choices(chars, k=k))

def make_report_id(year: int) -> str:
    return f"HK-{year}-{_rand(6)}"

def make_audit_id(year: int) -> str:
    return f"AUD-{year}-{_rand(8)}"

def make_ledger_id() -> str:
    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    return f"LED-{ts}-{_rand(4)}"


# ─────────────────────────────────────────────────────────────────
# ARTIFACT BUILDERS
# ─────────────────────────────────────────────────────────────────

def build_evidence_json(
    report_id: str,
    claims: list,
    absence_flag_ids: set,
    inferred_ratio: float,
    now: str,
) -> dict:
    """evidence.json — per-claim claim_flags[], root inferred_ratio."""
    entries = []
    for i, claim in enumerate(claims, 1):
        cid      = claim.get("claim_id", f"CLM-{i:03d}")
        ev_type  = claim.get("evidence_type", "INFERRED")
        # Build per-claim flags list
        claim_flags = list(claim.get("claim_flags", []) or [])
        if cid in absence_flag_ids:
            claim_flags.append("ABSENCE_ASSERTION")

        source = claim.get("source") or {
            "type":         "MODEL_REASONING",
            "uri":          None,
            "title":        "AI-generated inference",
            "retrieved_at": now,
            "excerpt":      claim.get("text", "")[:120],
        }
        entries.append({
            "claim_id":      cid,
            "claim_text":    claim.get("text", ""),
            "evidence_type": ev_type,
            "source":        source,
            "confidence":    claim.get("confidence", 0.5),
            "claim_flags":   claim_flags,
            "notes":         claim.get("notes", ""),
        })
    return {
        "report_id":      report_id,
        "generated_at":   now,
        "pipeline_version": PIPELINE_VERSION,
        "inferred_ratio": inferred_ratio,
        "entries":        entries,
    }


def build_sci_score_json(
    report_id: str,
    dims: dict,
    evid_raw: float,
    evid_effective: float,
    hci: float,
    cert_level: str,
    cert_extra: dict,
    inferred_ratio: float,
    ceiling_note: str | None,
    hallucination_flags: list,
    absence_flags: list,
    now: str,
) -> dict:
    # Aggregate all flag strings
    all_flags = []
    for f in absence_flags:
        all_flags.append(f["flag_type"])
    if hallucination_flags:
        all_flags.append("HALLUCINATION_DETECTED")

    obj = {
        "report_id":              report_id,
        "generated_at":           now,
        "pipeline_version":       PIPELINE_VERSION,
        "dimensions": {
            "EVID": {"score": dims["EVID"]["score"], "rationale": dims["EVID"].get("rationale", "")},
            "MECH": {"score": dims["MECH"]["score"], "rationale": dims["MECH"].get("rationale", "")},
            "INC":  {"score": dims["INC"]["score"],  "rationale": dims["INC"].get("rationale", "")},
            "RISK": {"score": dims["RISK"]["score"], "rationale": dims["RISK"].get("rationale", "")},
            "SPEC": {"score": dims["SPEC"]["score"], "rationale": dims["SPEC"].get("rationale", "")},
        },
        "evid_raw":               evid_raw,
        "evid_effective":         evid_effective,
        "hci":                    hci,
        "inferred_ratio":         inferred_ratio,
        "certification_level":    cert_level,
        "evid_ceiling_applied":   ceiling_note,
        "flags":                  all_flags,
        "hallucination_flags":    hallucination_flags,
        "absence_assertion_flags": absence_flags,
    }
    obj.update(cert_extra)
    return obj


def build_report_html(
    report_id: str,
    title: str,
    topic: str,
    summary: str,
    claims: list,
    sci: dict,
    now: str,
) -> str:
    cert           = sci["certification_level"]
    hci            = sci["hci"]
    dims           = sci["dimensions"]
    inferred_ratio = sci["inferred_ratio"]
    evid_eff       = sci["evid_effective"]
    meta           = CERT_META[cert]

    # Badge-level colours
    c_bg     = meta["bg"]
    c_border = meta["border"]
    c_text   = meta["text"]
    icon     = meta["icon"]

    # Claims HTML
    absence_ids  = {f["claim_id"] for f in sci.get("absence_assertion_flags", [])}
    claims_html  = ""
    for c in claims:
        cid   = c.get("claim_id", "CLM-?")
        ev    = c.get("evidence_type", "INFERRED")
        ev_col = "#34D399" if ev == "VERIFIED" else "#FBBF24"
        ab_badge = (
            '<span class="cbadge" style="background:#F87171">ABSENCE_ASSERTION</span>'
            if cid in absence_ids else ""
        )
        claims_html += f"""
        <div class="claim">
          <span class="cid">{cid}</span>
          <span class="cbadge" style="background:{ev_col}">{ev}</span>
          {ab_badge}
          <p>{c.get('text','')}</p>
        </div>"""

    # Dimension bars
    dim_rows = ""
    for key, label in [
        ("EVID", "Evidence Integrity"),
        ("MECH", "Mechanism Clarity"),
        ("INC",  "Incentive Decode"),
        ("RISK", "Risk Realism"),
        ("SPEC", "Specificity"),
    ]:
        score = dims[key]["score"] if key != "EVID" else evid_eff
        bar   = int(score * 10)
        dim_rows += f"""
        <tr>
          <td class="dname">{key}<span class="dlabel"> {label}</span></td>
          <td><div class="bar" style="width:{bar}%;background:{c_border}"></div></td>
          <td class="dscore">{score}</td>
        </tr>"""

    ceiling_notice = ""
    if sci.get("evid_ceiling_applied"):
        ceiling_notice = f"""
        <div class="notice">⚠️ <b>EVID Ceiling Applied:</b> {sci['evid_ceiling_applied']}</div>"""

    absence_notice = ""
    if sci.get("absence_assertion_flags"):
        ids = ", ".join(f["claim_id"] for f in sci["absence_assertion_flags"])
        absence_notice = f"""
        <div class="notice nwarn">🚩 <b>Absence Assertions Detected:</b> {ids}</div>"""

    pro_note = ""
    if sci.get("pro_requires_second_review"):
        pro_note = '<div class="notice">📋 <b>HK-PRO:</b> Second reviewer required before publication.</div>'
    if sci.get("institutional_requires_two_reviews"):
        pro_note = '<div class="notice">🏛 <b>HK-INSTITUTIONAL:</b> Two independent reviewers required.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — HumanKlu™</title>
  <style>
    :root{{--bg:#0F1117;--surf:#1A1D27;--brd:#2A2D3E;--txt:#E8EAF0;--mut:#8B8FA8;--acc:#6C63FF;
          --cb:{c_bg};--cbo:{c_border};--ct:{c_text};}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--txt);
          line-height:1.65;padding:2rem;max-width:860px;margin:0 auto}}
    .cert-badge{{display:inline-flex;align-items:center;gap:.55rem;
      background:var(--cb);border:2px solid var(--cbo);border-radius:999px;
      padding:.45rem 1.1rem;font-size:.82rem;font-weight:800;letter-spacing:.09em;
      color:var(--ct);margin-bottom:1rem;
      box-shadow:0 0 14px color-mix(in srgb,var(--cbo) 35%,transparent)}}
    header{{border-bottom:1px solid var(--brd);padding-bottom:1.5rem;margin-bottom:2rem}}
    h1{{font-size:1.8rem;font-weight:800;line-height:1.25;margin-bottom:.5rem}}
    .meta{{color:var(--mut);font-size:.85rem}}.meta span{{margin-right:1.5rem}}
    section{{margin:2rem 0}}
    h2{{font-size:1.05rem;font-weight:700;color:var(--acc);text-transform:uppercase;
        letter-spacing:.1em;margin-bottom:1rem}}
    .sumbox{{background:var(--surf);border-left:3px solid var(--acc);
             padding:1rem 1.25rem;border-radius:0 8px 8px 0}}
    .sci-card{{background:var(--surf);border:1px solid var(--brd);border-radius:12px;padding:1.5rem}}
    .sci-hdr{{display:flex;justify-content:space-between;align-items:flex-start;
              margin-bottom:1.5rem;flex-wrap:wrap;gap:.75rem}}
    .sci-hci{{font-size:2.5rem;font-weight:900;color:var(--ct)}}
    .sci-pill{{background:color-mix(in srgb,var(--cbo) 18%,transparent);
               color:var(--ct);border:1px solid color-mix(in srgb,var(--cbo) 45%,transparent);
               padding:.4rem 1rem;border-radius:999px;font-weight:700;font-size:.9rem;
               letter-spacing:.08em}}
    .sci-sub{{font-size:.78rem;color:var(--mut);margin-top:.3rem}}
    table.dims{{width:100%;border-collapse:collapse}}
    table.dims td{{padding:.5rem .75rem;vertical-align:middle}}
    .dname{{font-weight:700;font-size:.85rem;width:13rem;white-space:nowrap}}
    .dlabel{{font-weight:400;color:var(--mut);font-size:.78rem}}
    .bar{{height:8px;border-radius:4px;min-width:4px}}
    .dscore{{font-weight:700;font-size:.9rem;text-align:right;width:2.5rem}}
    .claim{{background:var(--surf);border:1px solid var(--brd);
            border-radius:8px;padding:1rem;margin-bottom:.75rem}}
    .claim p{{margin-top:.5rem;font-size:.93rem}}
    .cid{{font-size:.75rem;font-weight:700;color:var(--mut);font-family:monospace;margin-right:.4rem}}
    .cbadge{{font-size:.72rem;font-weight:700;padding:.15rem .6rem;
             border-radius:999px;color:#0F1117;letter-spacing:.05em;margin-right:.25rem}}
    .notice{{background:color-mix(in srgb,#FBBF24 12%,transparent);
             border:1px solid color-mix(in srgb,#FBBF24 35%,transparent);
             border-radius:8px;padding:.75rem 1rem;margin-bottom:.75rem;font-size:.88rem}}
    .nwarn{{background:color-mix(in srgb,#F87171 12%,transparent);
            border-color:color-mix(in srgb,#F87171 35%,transparent)}}
    footer{{margin-top:3rem;padding-top:1.5rem;border-top:1px solid var(--brd);
            color:var(--mut);font-size:.8rem;display:flex;
            justify-content:space-between;flex-wrap:wrap;gap:.5rem}}
    code{{font-family:monospace;font-size:.82rem;color:var(--acc);
          background:var(--surf);padding:.15rem .4rem;border-radius:4px}}
  </style>
</head>
<body>
  <header>
    <div class="cert-badge">{icon} HumanKlu™ · {cert}</div>
    <h1>{title}</h1>
    <div class="meta">
      <span>📋 {report_id}</span>
      <span>🕒 {now[:10]}</span>
      <span>🏷 {topic}</span>
      <span>⚗️ {PIPELINE_VERSION}</span>
    </div>
  </header>

  <section>
    <h2>Summary</h2>
    <div class="sumbox"><p>{summary}</p></div>
  </section>

  <section>
    <h2>Signal Confidence Index</h2>
    <div class="sci-card">
      <div class="sci-hdr">
        <div>
          <div style="color:var(--mut);font-size:.8rem;margin-bottom:.25rem">Human Calibration Index</div>
          <div class="sci-hci">{hci}<span style="font-size:1.2rem;color:var(--mut)">/10</span></div>
          <div class="sci-sub">Inferred: {inferred_ratio:.0%} of claims · EVID_eff: {evid_eff}</div>
        </div>
        <div style="text-align:right">
          <div class="sci-pill">{cert}</div>
        </div>
      </div>
      {ceiling_notice}
      {absence_notice}
      {pro_note}
      <table class="dims">{dim_rows}</table>
    </div>
  </section>

  <section>
    <h2>Claim Ledger</h2>
    {claims_html}
  </section>

  <footer>
    <span>HumanKlu™ {PIPELINE_VERSION} · © 2026 HumanKlu</span>
    <span>Report: <code>{report_id}</code></span>
  </footer>
</body>
</html>"""


def build_audit_json(
    report_id: str,
    sci: dict,
    artifact_hashes: dict,
    evid_raw: float,
    evid_effective: float,
    inferred_ratio: float,
    now: str,
) -> dict:
    cert   = sci["certification_level"]
    hci    = sci["hci"]
    dims   = sci["dimensions"]
    meta   = CERT_META[cert]
    year   = datetime.now(timezone.utc).year

    all_flags = list(sci.get("flags", []))

    obj = {
        "audit_id":           make_audit_id(year),
        "report_id":          report_id,
        "created_at":         now,
        "hkp_version":        "1.1",
        "pipeline_version":   PIPELINE_VERSION,
        "artifact_hashes":    artifact_hashes,
        "sci_summary": {
            "EVID":           dims["EVID"]["score"],
            "MECH":           dims["MECH"]["score"],
            "INC":            dims["INC"]["score"],
            "RISK":           dims["RISK"]["score"],
            "SPEC":           dims["SPEC"]["score"],
            "HCI":            hci,
        },
        "evid_raw":           evid_raw,
        "evid_effective":     evid_effective,
        "inferred_ratio":     inferred_ratio,
        "certification_level": cert,
        "evid_ceiling_applied": sci.get("evid_ceiling_applied"),
        "flags":              all_flags,
        "absence_assertion_flags": sci.get("absence_assertion_flags", []),
        "hallucination_flags": sci.get("hallucination_flags", []),
        "human_reviewer":     None,
        "badge": {
            "label":      meta["label"],
            "border_color": meta["border"],
            "text_color": meta["text"],
            "icon":       meta["icon"],
            "hci_display": f"{hci}/10",
        },
    }
    # Carry through cert-level extra fields
    for k in ("pro_requires_second_review", "institutional_requires_two_reviews"):
        if k in sci:
            obj[k] = sci[k]
    return obj


def build_ledger_entry(
    report_id: str,
    audit_id: str,
    cert_level: str,
    hci: float,
    evid_effective: float,
    inferred_ratio: float,
    author_model: str,
    prev_entry_id: str | None,
    now: str,
) -> dict:
    return {
        "entry_id":            make_ledger_id(),
        "timestamp":           now,
        "report_id":           report_id,
        "audit_id":            audit_id,
        "event_type":          "CREATED",
        "certification_level": cert_level,
        "hci":                 hci,
        "evid_effective":      evid_effective,
        "inferred_ratio":      inferred_ratio,
        "author_model":        author_model,
        "human_reviewer":      None,
        "notes":               "Initial pipeline run.",
        "prev_entry_id":       prev_entry_id,
    }


# ─────────────────────────────────────────────────────────────────
# HASHING
# ─────────────────────────────────────────────────────────────────
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────
def run_pipeline(input_path: str, output_dir: str, run_id: str = None) -> dict:
    with open(input_path) as f:
        inp = json.load(f)

    now       = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    year      = datetime.now(timezone.utc).year
    report_id = run_id or make_report_id(year)
    out       = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    claims = inp.get("claims", [])
    for i, c in enumerate(claims, 1):
        if "claim_id" not in c:
            c["claim_id"] = f"CLM-{i:03d}"

    dims = inp.get("dimensions", {
        "EVID": {"score": 5.0, "rationale": "Default."},
        "MECH": {"score": 5.0, "rationale": "Default."},
        "INC":  {"score": 5.0, "rationale": "Default."},
        "RISK": {"score": 5.0, "rationale": "Default."},
        "SPEC": {"score": 5.0, "rationale": "Default."},
    })
    hallucination_flags = inp.get("hallucination_flags", [])
    author_model        = inp.get("author", {}).get("model_version", "unknown")

    # ── v1.1: inferred ratio ──────────────────────────────────────
    inferred_ratio = compute_inferred_ratio(claims)

    # ── v1.1: EVID ceiling ───────────────────────────────────────
    evid_raw                  = dims["EVID"]["score"]
    evid_effective, ceiling_note = apply_evid_ceiling(evid_raw, inferred_ratio)

    # ── v1.1: absence assertion detection ────────────────────────
    absence_flags     = detect_absence_assertions(claims)
    absence_flag_ids  = {f["claim_id"] for f in absence_flags}
    has_absence       = bool(absence_flags)

    print(f"  ℹ  inferred_ratio={inferred_ratio:.4f}  EVID_raw={evid_raw}  EVID_eff={evid_effective}")
    if ceiling_note:
        print(f"  ⚠  {ceiling_note}")
    if absence_flags:
        print(f"  🚩 {len(absence_flags)} ABSENCE_ASSERTION flag(s)")

    # ── HCI  (uses evid_effective) ────────────────────────────────
    hci = compute_hci(dims, evid_effective)

    # ── Certification level ───────────────────────────────────────
    cert_level, cert_extra = determine_certification_level(
        dims, evid_effective, hci, inferred_ratio, hallucination_flags, has_absence
    )

    # ── 1. evidence.json ─────────────────────────────────────────
    evidence = build_evidence_json(report_id, claims, absence_flag_ids, inferred_ratio, now)
    ev_path  = out / "evidence.json"
    ev_path.write_text(json.dumps(evidence, indent=2))
    print("  ✓ evidence.json")

    # ── 2. sci_score.json ────────────────────────────────────────
    sci      = build_sci_score_json(
        report_id, dims, evid_raw, evid_effective, hci,
        cert_level, cert_extra, inferred_ratio, ceiling_note,
        hallucination_flags, absence_flags, now
    )
    sci_path = out / "sci_score.json"
    sci_path.write_text(json.dumps(sci, indent=2))
    print(f"  ✓ sci_score.json  (HCI={hci}  CERT={cert_level}  EVID_eff={evid_effective})")

    # ── 3. report.html ───────────────────────────────────────────
    html      = build_report_html(
        report_id, inp["title"], inp.get("topic", "General"),
        inp.get("summary", ""), claims, sci, now
    )
    html_path = out / "report.html"
    html_path.write_text(html)
    print("  ✓ report.html")

    # ── 4. humanklu_audit.json ───────────────────────────────────
    hashes = {
        "report_html":    sha256_file(str(html_path)),
        "evidence_json":  sha256_file(str(ev_path)),
        "sci_score_json": sha256_file(str(sci_path)),
    }
    audit      = build_audit_json(
        report_id, sci, hashes, evid_raw, evid_effective, inferred_ratio, now
    )
    audit_path = out / "humanklu_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2))
    print(f"  ✓ humanklu_audit.json  (audit_id={audit['audit_id']})")

    # ── 5. ledger.jsonl ──────────────────────────────────────────
    ledger_path = Path(output_dir).parent.parent / "ledger.jsonl"
    prev_id = None
    if ledger_path.exists():
        lines = ledger_path.read_text().strip().splitlines()
        if lines:
            try:
                prev_id = json.loads(lines[-1])["entry_id"]
            except Exception:
                pass
    entry = build_ledger_entry(
        report_id, audit["audit_id"], cert_level, hci,
        evid_effective, inferred_ratio, author_model, prev_id, now
    )
    with open(ledger_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  ✓ ledger.jsonl  (entry={entry['entry_id']})")

    print(f"\n  🎯 Pipeline complete → {out.resolve()}")
    return {
        "report_id":           report_id,
        "certification_level": cert_level,
        "hci":                 hci,
        "evid_raw":            evid_raw,
        "evid_effective":      evid_effective,
        "inferred_ratio":      inferred_ratio,
        "flags":               sci.get("flags", []),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"HumanKlu™ Artifact Pipeline {PIPELINE_VERSION}")
    parser.add_argument("--input",  required=True, help="Path to input JSON")
    parser.add_argument("--output", required=True, help="Output directory for this run")
    parser.add_argument("--run-id", default=None,  help="Optional deterministic report ID")
    args = parser.parse_args()
    print(f"\n🔬 HumanKlu™ Pipeline {PIPELINE_VERSION} — starting run\n")
    result = run_pipeline(args.input, args.output, args.run_id)
    print(f"\n  Final: {json.dumps(result, indent=2)}\n")
