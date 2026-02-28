# HumanKlu™ — Inkluso Division Deploy Guide

## Hosting on GitHub Pages

1. Push the `humanklu/` directory to a GitHub repo
2. Enable GitHub Pages from repo Settings → Pages → Source: main branch
3. The site will be available at `https://<user>.github.io/<repo>/division_humanklu/`

## Directory Structure Assumptions

The division site expects the `batch_run/` directory to be a sibling of `division_humanklu/`:

```
humanklu/
├── division_humanklu/    ← this package
│   ├── index.html
│   ├── methodology.html
│   └── case-studies/
│       ├── index.html
│       └── case_studies.json
├── batch_run/            ← must be present at this level
│   ├── runs/
│   │   ├── 01_rejected/report.html
│   │   ├── 02_reviewed/report.html
│   │   ├── 03_verified/report.html
│   │   ├── 04_pro/report.html
│   │   └── 05_institutional/report.html
│   ├── summary.json
│   └── summary.csv
├── scripts/
│   ├── pipeline.py
│   └── batch_run.py
└── inputs/
```

Case study links use relative paths: `../../batch_run/runs/<run_id>/report.html`

## Regenerating After New Batch Runs

1. Run the batch pipeline:
   ```bash
   python scripts/batch_run.py --inputs ./inputs --output ./batch_run
   ```

2. Update `division_humanklu/case-studies/case_studies.json` with new run metadata from `batch_run/summary.json`

3. Update the distribution stats in `division_humanklu/index.html` (counts_by_level, avg_hci, avg_evid_effective, avg_inferred_ratio)

4. Commit and push — GitHub Pages will redeploy automatically

## Local Preview

```bash
cd humanklu/
python -m http.server 8080
# Open http://localhost:8080/division_humanklu/
```
