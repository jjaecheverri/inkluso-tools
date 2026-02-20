// IN-KluSo Tools — OPS Lab Request Generator

function buildOPSRequest() {
  const biz_type = document.getElementById('biz_type').value.trim();
  const city = document.getElementById('city').value.trim();
  const problem = document.getElementById('problem').value.trim();
  const revenue = document.getElementById('revenue').value;
  const pressure = document.getElementById('pressure').value;
  const horizon = document.getElementById('horizon').value;
  const risk = document.getElementById('risk').value;
  const budget_raw = document.getElementById('budget').value.trim();

  if (!biz_type) { alert('Business type is required.'); return null; }
  if (!city) { alert('City or region is required.'); return null; }
  if (!problem) { alert('Core problem description is required.'); return null; }

  const budget = budget_raw ? parseFloat(budget_raw) : null;
  const run_id = makeRunId([biz_type, city, pressure, horizon]);

  const request = {
    packet_id: "INKLUSO_OPS_REQUEST",
    version: "1.0.0",
    tool_name: "ops_lab",
    run_id: run_id,
    created_at_iso: new Date().toISOString(),
    inputs: {
      business_type: biz_type,
      city_or_region: city,
      core_problem: problem,
      monthly_revenue_range: revenue,
      primary_pressure: pressure,
      time_horizon: horizon,
      risk_tolerance: risk,
      ...(budget !== null && { budget_available: budget })
    },
    output_contract: {
      required_files: [
        `/outputs/ops/${run_id}/plan.html`,
        `/outputs/ops/${run_id}/plan.json`,
        `/outputs/ops/${run_id}/audit.yaml`
      ],
      plan_format: "IN-KluSo branded HTML with: Problem Summary, Diagnosis, Constraints, 3 Intervention Tracks (Low-capital / Structural / Defensive), Metrics, First Irreversible Step, Risks",
      plan_json_format: "JSON: classification, assumptions[], interventions[], metrics[], first_irreversible_step, risks[], decision_window",
      audit_format: "YAML: scope_limits, assumptions, uncertainty_notes, safety_notes"
    },
    safety_rules: [
      "No legal or medical advice. Provide operational options and prompt to consult licensed professionals where appropriate.",
      "No guaranteed outcomes. All projections must include explicit assumptions and downside risks.",
      "Action plans must include measurable leading indicators and identify the first irreversible step.",
      "Distinguish between actions that are reversible and actions that commit capital or contracts.",
      "Do not recommend actions that require regulatory compliance without flagging the requirement explicitly."
    ],
    execution_notes: "Paste this packet into Tasklet. Run OPS Lab diagnosis workflow. Produce all three output files and commit to repo under output_contract paths. Notify requester when published."
  };

  return { request, run_id };
}

document.addEventListener('DOMContentLoaded', () => {
  let lastRequest = null;

  document.getElementById('btn-generate').addEventListener('click', () => {
    const result = buildOPSRequest();
    if (!result) return;
    lastRequest = result.request;
    showPreview('output-box', lastRequest);
    document.getElementById('btn-download').disabled = false;
    document.getElementById('btn-copy').disabled = false;
  });

  document.getElementById('btn-download').addEventListener('click', () => {
    if (!lastRequest) return;
    downloadJSON(lastRequest, `ops-request-${lastRequest.run_id}.json`);
  });

  document.getElementById('btn-copy').addEventListener('click', () => {
    if (!lastRequest) return;
    copyToClipboard(JSON.stringify(lastRequest, null, 2), 'copy-notice');
  });
});
