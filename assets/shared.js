// IN-KluSo Tools — Shared Utilities

// Simple deterministic hash (djb2 variant)
function hashString(str) {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i);
    hash = hash & hash; // 32-bit
  }
  return Math.abs(hash).toString(36);
}

// Stable slug from key inputs
function makeRunId(parts) {
  const raw = parts.filter(Boolean).join('_').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  const h = hashString(raw).slice(0, 6);
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  return `${raw.slice(0, 40)}-${today}-${h}`;
}

// Download JSON file
function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

// Copy to clipboard
function copyToClipboard(text, noticeId) {
  navigator.clipboard.writeText(text).then(() => {
    const el = document.getElementById(noticeId);
    if (el) { el.classList.add('visible'); setTimeout(() => el.classList.remove('visible'), 2000); }
  });
}

// Show JSON preview in output box
function showPreview(boxId, data) {
  const box = document.getElementById(boxId);
  if (!box) return;
  box.querySelector('pre').textContent = JSON.stringify(data, null, 2);
  box.classList.add('visible');
}
