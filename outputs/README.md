# /outputs — IN-KluSo Tools Output Archive

This folder contains published outputs from CI and OPS Lab requests.

## Structure

```
/outputs/
  /ci/
    /sample_run/          ← Sample CI output (Bentonville cultural signal)
      article.html        ← Branded IN-KluSo report
      evidence.json       ← Sources and claim mapping
      audit.yaml          ← Verification log
    /<run_id>/            ← Future runs, one folder per request
  /ops/
    /sample_run/          ← Sample OPS output (restaurant margin pressure)
      plan.html           ← Branded intervention plan
      plan.json           ← Structured plan data
      audit.yaml          ← Scope limits and assumptions
    /<run_id>/            ← Future runs, one folder per request
```

## Naming Convention

`run_id` format: `{slug}-{YYYYMMDD}-{6-char-hash}`

Example: `bentonville-ar-90d-en-20250120-4x7r2k`

The slug is derived from the inputs (city + parameters). The date is when the request was generated. The hash ensures uniqueness when the same city is requested multiple times.

When committing a new output, create a folder at `/outputs/ci/<run_id>/` or `/outputs/ops/<run_id>/` and add all three required files.

## Viewing Outputs

Published outputs are live on GitHub Pages:
- CI sample: `https://jjaecheverri.github.io/inkluso-tools/outputs/ci/sample_run/article.html`
- OPS sample: `https://jjaecheverri.github.io/inkluso-tools/outputs/ops/sample_run/plan.html`
