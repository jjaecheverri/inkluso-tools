// IN-KluSo Tools — CI Request Generator

function buildCIRequest() {
  const city = document.getElementById('city').value.trim();
  const window_days = parseInt(document.getElementById('window_days').value) || 90;
  const neighborhood = document.getElementById('neighborhood').value.trim();
  const language = document.getElementById('language').value;
  const topic_raw = document.getElementById('topic_gravity').value.trim();
  const strictness = document.getElementById('strictness').value;

  if (!city) { alert('City or region is required.'); return null; }

  const topics = topic_raw ? topic_raw.split(',').map(t => t.trim()).filter(Boolean) : [];
  const run_id = makeRunId([city, neighborhood || '', `${window_days}d`, language]);

  const request = {
    packet_id: "INKLUSO_CI_REQUEST",
    version: "1.0.0",
    tool_name: "cultural_intelligence",
    run_id: run_id,
    created_at_iso: new Date().toISOString(),
    inputs: {
      city_or_region: city,
      time_window_days: window_days,
      ...(neighborhood && { neighborhood_or_corridor: neighborhood }),
      language_preference: language,
      ...(topics.length && { topic_gravity: topics }),
      evidence_strictness: strictness
    },
    output_contract: {
      required_files: [
        `/outputs/ci/${run_id}/article.html`,
        `/outputs/ci/${run_id}/evidence.json`,
        `/outputs/ci/${run_id}/audit.yaml`
      ],
      article_format: "IN-KluSo branded HTML with sections: CORE / THRUST / AXIS / FLOW / GROUND + Evidence Box + Verified vs Inferred Box",
      evidence_format: "JSON: sources[] with title/publisher/url/publish_date/accessed_date; claims[] mapping claim to source_ids",
      audit_format: "YAML: verify_summary, inference_summary, risk_flags, refusal_checks"
    },
    safety_rules: [
      "No private individuals. Public businesses and entities only if verifiable.",
      "Minimum 5 sources with publish dates. Map all key claims to source IDs.",
      "Separate VERIFIED statements from INFERRED statements explicitly in output.",
      "No accusations of criminal conduct without authoritative primary sources. If unavailable, refuse and document.",
      "No partisan political framing. Center lived experience and behavioral adjustment.",
      "No crime voyeurism. Signal = structural shift, not incident reporting."
    ],
    execution_notes: "Paste this packet into Tasklet. Run GS-CI research workflow (5 stages: REGION SCOPE → HUNT → SCREEN → VERIFY → BUILD DOSSIER). Commit outputs to repo under output_contract paths. Notify requester when published."
  };

  return { request, run_id };
}

document.addEventListener('DOMContentLoaded', () => {
  let lastRequest = null;

  document.getElementById('btn-generate').addEventListener('click', () => {
    const result = buildCIRequest();
    if (!result) return;
    lastRequest = result.request;
    showPreview('output-box', lastRequest);
    document.getElementById('btn-download').disabled = false;
    document.getElementById('btn-copy').disabled = false;
  });

  document.getElementById('btn-download').addEventListener('click', () => {
    if (!lastRequest) return;
    downloadJSON(lastRequest, `ci-request-${lastRequest.run_id}.json`);
  });

  document.getElementById('btn-copy').addEventListener('click', () => {
    if (!lastRequest) return;
    copyToClipboard(JSON.stringify(lastRequest, null, 2), 'copy-notice');
  });
});
