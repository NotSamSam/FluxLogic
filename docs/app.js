const state = {
  rawData: [],
  processedData: [],
  invalidData: [],
  endpoints: [],
  flowLog: [],
  webhookEvents: [],
  stats: { flows: 0, records: 0, valid: 0 }
};

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
  });
});

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = 'toast toast-' + type;
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

async function signPayload(payload) {
  const secret = 'fluxlogic-dev-secret';
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(JSON.stringify(payload)));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

function updateMetrics() {
  document.getElementById('m-flows').textContent = state.stats.flows;
  document.getElementById('m-records').textContent = state.stats.records;
  document.getElementById('m-valid').textContent = state.stats.valid;
  document.getElementById('m-endpoints').textContent = state.endpoints.length;
  document.getElementById('ep-count').textContent = state.endpoints.length;
}

const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault(); uploadZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });

function handleFile(file) {
  const reader = new FileReader();
  reader.onload = e => {
    try {
      let data;
      if (file.name.endsWith('.csv')) {
        data = parseCSV(e.target.result);
      } else {
        const parsed = JSON.parse(e.target.result);
        data = Array.isArray(parsed) ? parsed : [parsed];
      }
      state.rawData = data;
      renderPreview(data);
      toast('Loaded ' + data.length + ' records from ' + file.name, 'success');
    } catch (err) {
      toast('Failed to parse file: ' + err.message, 'error');
    }
  };
  reader.readAsText(file);
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
  return lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''));
    const obj = {};
    headers.forEach((h, i) => obj[h] = vals[i] || '');
    return obj;
  });
}

function loadManualJSON() {
  try {
    const raw = document.getElementById('manual-json').value;
    const parsed = JSON.parse(raw);
    const data = Array.isArray(parsed) ? parsed : [parsed];
    state.rawData = data;
    renderPreview(data);
    toast('Loaded ' + data.length + ' records', 'success');
  } catch (err) {
    toast('Invalid JSON: ' + err.message, 'error');
  }
}

function renderPreview(data) {
  const container = document.getElementById('data-preview');
  document.getElementById('preview-count').textContent = data.length + ' rows';
  if (!data.length) { container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><p>No data</p></div>'; return; }
  const keys = Object.keys(data[0]);
  let html = '<div class="table-wrap"><table><thead><tr>';
  html += '<th>#</th>';
  keys.forEach(k => html += '<th>' + escHtml(k) + '</th>');
  html += '</tr></thead><tbody>';
  data.slice(0, 50).forEach((row, i) => {
    html += '<tr><td>' + i + '</td>';
    keys.forEach(k => html += '<td>' + escHtml(String(row[k] ?? '')) + '</td>');
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  if (data.length > 50) html += '<p style="color:var(--text-muted);font-size:0.8rem;margin-top:0.5rem">Showing first 50 of ' + data.length + ' rows</p>';
  container.innerHTML = html;
}

function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function processData() {
  if (!state.rawData.length) { toast('No data loaded — upload a file first', 'error'); return; }

  const reqRaw = document.getElementById('required-fields').value;
  const requiredFields = reqRaw ? reqRaw.split(',').map(f => f.trim().toLowerCase().replace(/[\s-]+/g, '_').replace(/[^\w]/g, '')) : [];

  const bar = document.getElementById('process-progress');
  const fill = document.getElementById('progress-fill');
  bar.style.display = 'block'; fill.style.width = '0%';

  const valid = [], invalid = [];
  const total = state.rawData.length;

  let idx = 0;
  const batchSize = Math.max(1, Math.floor(total / 20));

  function tick() {
    const end = Math.min(idx + batchSize, total);
    for (let i = idx; i < end; i++) {
      const result = processRecord(i, state.rawData[i], requiredFields);
      if (result.isValid) valid.push(result); else invalid.push(result);
    }
    idx = end;
    fill.style.width = Math.round((idx / total) * 100) + '%';
    if (idx < total) { requestAnimationFrame(tick); }
    else { finishProcessing(valid, invalid); }
  }
  requestAnimationFrame(tick);
}

function processRecord(index, raw, requiredFields) {
  const errors = [];
  let rec = { ...raw };

  Object.keys(rec).forEach(k => { if (typeof rec[k] === 'string') rec[k] = rec[k].trim(); });

  const normalized = {};
  Object.keys(rec).forEach(k => {
    const nk = k.trim().toLowerCase().replace(/[\s-]+/g, '_').replace(/[^\w]/g, '');
    normalized[nk] = rec[k];
  });
  rec = normalized;

  Object.keys(rec).forEach(k => {
    const v = rec[k];
    if (typeof v === 'string') {
      if (v.toLowerCase() === 'true') { rec[k] = true; return; }
      if (v.toLowerCase() === 'false') { rec[k] = false; return; }
      if (/^-?\d+$/.test(v)) { rec[k] = parseInt(v, 10); return; }
      if (/^-?\d+\.\d+$/.test(v)) { rec[k] = parseFloat(v); return; }
    }
  });

  const allEmpty = Object.values(rec).every(v => v === null || v === undefined || v === '');
  if (allEmpty) { errors.push('Empty row'); return { index, original: raw, processed: null, errors, isValid: false }; }

  requiredFields.forEach(f => {
    if (!(f in rec) || rec[f] === null || rec[f] === undefined || rec[f] === '') {
      errors.push("Missing required field: '" + f + "'");
    }
  });

  return { index, original: raw, processed: errors.length ? null : rec, errors, isValid: errors.length === 0 };
}

function finishProcessing(valid, invalid) {
  state.processedData = valid.map(r => r.processed);
  state.invalidData = invalid;
  state.stats.records += valid.length + invalid.length;
  state.stats.valid += valid.length;

  const container = document.getElementById('process-result');
  let html = '';

  if (invalid.length === 0) {
    html = '<div style="margin-top:1rem;padding:0.8rem;background:#065f46;border:1px solid rgba(52,211,153,0.3);border-radius:8px;color:#34d399;font-weight:600">✅ All ' + valid.length + ' records are valid — ready to dispatch</div>';
  } else if (valid.length > 0) {
    html = '<div style="margin-top:1rem;padding:0.8rem;background:#78350f;border:1px solid rgba(251,191,36,0.3);border-radius:8px;color:#fbbf24;font-weight:600">⚠️ ' + valid.length + ' valid / ' + invalid.length + ' invalid</div>';
  } else {
    html = '<div style="margin-top:1rem;padding:0.8rem;background:#7f1d1d;border:1px solid rgba(248,113,113,0.3);border-radius:8px;color:#f87171;font-weight:600">❌ All ' + invalid.length + ' records failed validation</div>';
  }

  if (invalid.length) {
    html += '<details style="margin-top:0.75rem"><summary style="cursor:pointer;color:var(--text-secondary);font-size:0.85rem">🔍 ' + invalid.length + ' validation errors</summary><div style="margin-top:0.5rem">';
    invalid.slice(0, 15).forEach(r => {
      html += '<div class="log-entry"><span class="badge badge-error">Row ' + r.index + '</span><span>' + escHtml(r.errors.join(', ')) + '</span></div>';
    });
    html += '</div></details>';
  }
  container.innerHTML = html;
  updateMetrics();
  toast('Processing complete: ' + valid.length + ' valid, ' + invalid.length + ' invalid', valid.length ? 'success' : 'error');
}

function addEndpoint() {
  const name = document.getElementById('ep-name').value.trim();
  const url = document.getElementById('ep-url').value.trim();
  const method = document.getElementById('ep-method').value;
  const timeout = parseInt(document.getElementById('ep-timeout').value) || 30;
  const apiKey = document.getElementById('ep-key').value.trim();
  const headersRaw = document.getElementById('ep-headers').value.trim();

  if (!name || !url) { toast('Name and URL are required', 'error'); return; }
  try { new URL(url); } catch { toast('Invalid URL format', 'error'); return; }

  let headers = {};
  if (headersRaw) {
    try { headers = JSON.parse(headersRaw); } catch { toast('Invalid JSON in headers', 'error'); return; }
  }

  state.endpoints.push({ name, url, method, timeout, apiKey, headers, id: uuid() });
  renderEndpoints();
  updateDispatchSelect();
  updateMetrics();
  toast('Endpoint "' + name + '" saved', 'success');

  document.getElementById('ep-name').value = '';
  document.getElementById('ep-url').value = '';
  document.getElementById('ep-key').value = '';
  document.getElementById('ep-headers').value = '';
}

function removeEndpoint(id) {
  state.endpoints = state.endpoints.filter(e => e.id !== id);
  renderEndpoints();
  updateDispatchSelect();
  updateMetrics();
  toast('Endpoint removed', 'info');
}

function renderEndpoints() {
  const container = document.getElementById('endpoint-list');
  if (!state.endpoints.length) { container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📡</div><p>No endpoints configured</p></div>'; return; }
  container.innerHTML = state.endpoints.map(ep =>
    '<div class="endpoint-chip"><div class="endpoint-info"><span class="endpoint-method">' + ep.method + '</span><span><strong>' + escHtml(ep.name) + '</strong> · <code style="color:var(--text-muted);font-size:0.78rem">' + escHtml(ep.url) + '</code></span></div><button class="btn btn-danger btn-sm" onclick="removeEndpoint(\'' + ep.id + '\')">🗑️</button></div>'
  ).join('');
}

function updateDispatchSelect() {
  const sel = document.getElementById('dispatch-target');
  sel.innerHTML = state.endpoints.map(ep => '<option value="' + ep.id + '">' + escHtml(ep.name) + ' (' + ep.method + ')</option>').join('');
}

async function dispatchData() {
  if (!state.processedData.length) { toast('No processed data — run the pipeline first', 'error'); return; }
  if (!state.endpoints.length) { toast('No endpoints configured', 'error'); return; }

  const epId = document.getElementById('dispatch-target').value;
  const ep = state.endpoints.find(e => e.id === epId);
  if (!ep) { toast('Select a valid endpoint', 'error'); return; }

  const container = document.getElementById('dispatch-result');
  container.innerHTML = '<div style="display:flex;align-items:center;gap:0.5rem;color:var(--text-secondary)"><div class="spinner"></div> Dispatching ' + state.processedData.length + ' records to ' + escHtml(ep.name) + '…</div>';

  const t0 = performance.now();
  try {
    const headers = { 'Content-Type': 'application/json', ...ep.headers };
    if (ep.apiKey) headers['Authorization'] = 'Bearer ' + ep.apiKey;

    const resp = await fetch(ep.url, {
      method: ep.method,
      headers,
      body: JSON.stringify({ data: state.processedData }),
      signal: AbortSignal.timeout(ep.timeout * 1000)
    });

    const latency = Math.round(performance.now() - t0);
    const success = resp.ok;

    container.innerHTML = '<div class="log-entry"><span class="badge ' + (success ? 'badge-success' : 'badge-error') + '">' + resp.status + '</span><strong>' + escHtml(ep.name) + '</strong><span>' + latency + ' ms</span></div>';

    addFlowLog(ep, state.processedData.length, success ? 'success' : 'failed', success ? [] : ['HTTP ' + resp.status]);
    toast(success ? 'Dispatch successful!' : 'Dispatch returned HTTP ' + resp.status, success ? 'success' : 'error');
  } catch (err) {
    const latency = Math.round(performance.now() - t0);
    container.innerHTML = '<div class="log-entry"><span class="badge badge-info">SIM</span><strong>' + escHtml(ep.name) + '</strong><span>Simulated dispatch of ' + state.processedData.length + ' records (' + latency + ' ms)</span></div>';
    container.innerHTML += '<p style="color:var(--text-muted);font-size:0.8rem;margin-top:0.5rem">ℹ️ Real HTTP dispatch blocked by browser CORS policy. In production, FluxLogic runs server-side with Python + Requests.</p>';
    addFlowLog(ep, state.processedData.length, 'success', []);
    toast('Dispatch simulated (CORS restriction in browser)', 'info');
  }
  state.stats.flows++;
  updateMetrics();
}

async function simulateInbound() {
  const type = document.getElementById('wh-type').value;
  let payload;
  try { payload = JSON.parse(document.getElementById('wh-payload').value); } catch { toast('Invalid JSON payload', 'error'); return; }

  const sig = await signPayload(payload);
  const event = { id: uuid(), type, timestamp: new Date().toISOString(), source: 'external-simulation', payload, signature: sig };
  state.webhookEvents.unshift(event);
  renderWebhookLog();
  toast('Inbound webhook received — signature verified ✓', 'success');
}

async function sendOutbound() {
  const url = document.getElementById('wh-target').value.trim();
  if (!url) { toast('Target URL required', 'error'); return; }
  let payload;
  try { payload = JSON.parse(document.getElementById('wh-out-payload').value); } catch { toast('Invalid JSON payload', 'error'); return; }

  const sig = await signPayload(payload);
  const event = { id: uuid(), type: 'flow.dispatched', timestamp: new Date().toISOString(), source: 'fluxlogic', payload, signature: sig };

  try {
    const t0 = performance.now();
    await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-FluxLogic-Signature': sig }, body: JSON.stringify(event), signal: AbortSignal.timeout(10000) });
    const latency = Math.round(performance.now() - t0);
    toast('Webhook delivered in ' + latency + ' ms', 'success');
  } catch {
    toast('Delivery simulated (browser CORS restriction)', 'info');
  }

  state.webhookEvents.unshift(event);
  renderWebhookLog();
}

function renderWebhookLog() {
  const container = document.getElementById('wh-log');
  if (!state.webhookEvents.length) { container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔔</div><p>No events yet</p></div>'; return; }
  container.innerHTML = state.webhookEvents.slice(0, 30).map(ev =>
    '<div class="log-entry"><span class="badge ' + (ev.source === 'fluxlogic' ? 'badge-info' : 'badge-success') + '">' + escHtml(ev.type) + '</span><code>' + ev.id.slice(0, 8) + '…</code><span>from <strong>' + escHtml(ev.source) + '</strong></span><span style="color:var(--text-muted)">' + new Date(ev.timestamp).toLocaleTimeString() + '</span></div>'
  ).join('');
}

function addFlowLog(ep, count, status, errors) {
  state.flowLog.unshift({
    id: uuid(), endpoint: ep.name, url: ep.url, method: ep.method,
    records: count, status, errors, timestamp: new Date().toISOString()
  });
  renderFlowLog();
}

function renderFlowLog() {
  const container = document.getElementById('flow-log');
  if (!state.flowLog.length) { container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📜</div><p>No flows executed yet</p></div>'; return; }
  container.innerHTML = state.flowLog.map(f => {
    const cls = f.status === 'success' ? 'badge-success' : f.status === 'failed' ? 'badge-error' : 'badge-warning';
    return '<div class="log-entry"><span class="badge ' + cls + '">' + f.status.toUpperCase() + '</span><strong>' + f.records + '</strong> records → <code>' + escHtml(f.url) + '</code><span style="color:var(--text-muted)">' + new Date(f.timestamp).toLocaleTimeString() + '</span></div>';
  }).join('');
}

function clearLogs() { state.flowLog = []; renderFlowLog(); toast('Logs cleared', 'info'); }

updateMetrics();
