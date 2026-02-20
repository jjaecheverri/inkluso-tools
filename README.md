# IN-KluSo Tools

**A human-in-the-loop research layer for the IN-KluSo magazine.**

Two tools that let readers submit a structured intelligence request and receive a published, branded IN-KluSo report.

Live site: `https://jjaecheverri.github.io/inkluso-tools/`

---

## What's included

| File | Purpose |
|---|---|
| `/index.html` | Homepage — explains the workflow |
| `/tools/index.html` | Tools directory |
| `/tools/ci.html` | CI Request Generator form |
| `/tools/ops.html` | OPS Lab Request Generator form |
| `/assets/styles.css` | All styles (IN-KluSo brand) |
| `/assets/shared.js` | Shared utilities (hash, download, clipboard) |
| `/assets/ci.js` | CI form logic and JSON generation |
| `/assets/ops.js` | OPS form logic and JSON generation |
| `/outputs/` | Published output archive |

---

## GitHub Pages setup

1. Push this repo to GitHub (public repository)
2. Go to **Settings → Pages**
3. Under **Source**, select **Deploy from a branch**
4. Choose **main** branch, **/ (root)** folder
5. Click **Save**
6. Site will be live at `https://jjaecheverri.github.io/inkluso-tools/` within 2 minutes

---

## Run locally

```bash
# Python 3
python3 -m http.server 8080

# Then open:
# http://localhost:8080
```

No build step. No dependencies. It's just HTML.

---

## Human-in-the-loop workflow

```
Reader fills form
      ↓
Downloads or copies JSON request packet
      ↓
Pastes packet into Tasklet chat
      ↓
Tasklet runs research / diagnosis workflow
      ↓
Output committed to /outputs/<tool>/<run_id>/
      ↓
Page goes live on GitHub Pages
      ↓
Reader receives link to branded report
```

---

## Output folder placement

When a request is processed and outputs are ready:

1. Create folder: `/outputs/ci/<run_id>/` or `/outputs/ops/<run_id>/`
2. Add three files:
   - CI: `article.html`, `evidence.json`, `audit.yaml`
   - OPS: `plan.html`, `plan.json`, `audit.yaml`
3. Commit and push — GitHub Pages auto-publishes

The `run_id` is included in every request JSON packet under the `run_id` field.

---

## Tasklet prompt templates

### CI Request

```
Run this CI request.

[paste full JSON packet here]

Follow the GS-CI 5-stage research workflow:
1. REGION SCOPE — confirm city/corridor/timeframe
2. HUNT — 12–25 candidate signals across 6+ channels
3. SCREEN — score top 3 on signal strength, verifiability, micro-specificity
4. VERIFY — confirm with primary sources, build verification log
5. BUILD — write article.html, evidence.json, audit.yaml in IN-KluSo brand

Commit outputs to the path in output_contract. Notify me when published.
```

### OPS Request

```
Run this OPS request.

[paste full JSON packet here]

Diagnose the mechanism behind the pressure (not just the symptom).
Produce three intervention tracks: Low-capital / Structural / Defensive.
Include: measurable metrics, first irreversible step, explicit risks and assumptions.
Format output as plan.html, plan.json, audit.yaml in IN-KluSo brand.

Commit outputs to the path in output_contract. Notify me when published.
```

---

## Authors

Juan Camilo Echeverri & Camilo Osorio — IN-KluSo / Xtatik
