from flask import Blueprint, render_template_string
from .security import require_admin
from .db import connect

bp = Blueprint("dashboard", __name__)

DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Zentrix Device Connect</title>
<style>
:root{font-family:system-ui,sans-serif;color:#172033;background:#f3f6fb}
*{box-sizing:border-box}
body{margin:0}
header{background:#132b50;color:white;padding:22px}
header h1{margin:0;font-size:1.5rem}
header p{margin:6px 0 0;color:#d5e4fa}
main{max-width:1100px;margin:auto;padding:18px}
section,.card{background:white;border:1px solid #e1e7f0;border-radius:12px;padding:16px;margin-bottom:16px}
h2{font-size:1.15rem;margin-top:0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px}
.stat{background:white;border:1px solid #e1e7f0;border-radius:12px;padding:16px}
.stat span{display:block;color:#52627a;font-size:.9rem}
.stat strong{display:block;font-size:1.7rem;margin-top:5px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
input,button{font:inherit;padding:10px;border:1px solid #ccd5e3;border-radius:8px}
input{max-width:100%}
button{cursor:pointer;background:#174a86;color:white;border:0}
button.secondary{background:#52627a}
button:disabled{opacity:.55;cursor:wait}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:10px;border-bottom:1px solid #e7ecf3;overflow-wrap:anywhere}
.wrap{overflow-x:auto}
.badge{font-weight:700}
.online{color:#087a43}.offline{color:#b42318}
.note{color:#52627a;font-size:.9rem}
#message{white-space:pre-wrap;margin:12px 0}
#tokenBox{display:none;background:#fff7db;padding:12px;border-radius:8px;overflow-wrap:anywhere}
@media(max-width:600px){main{padding:10px}section{padding:12px}th,td{padding:7px;font-size:.9rem}}
</style>
</head>
<body>
<header>
<h1>Zentrix Device Connect</h1>
<p>Administrator dashboard · Device management</p>
</header>
<main>
<div id="message" role="status" aria-live="polite"></div>
<div class="stats" id="stats">
<div class="stat"><span>Devices</span><strong>—</strong></div>
<div class="stat"><span>Surveys</span><strong>—</strong></div>
<div class="stat"><span>Survey responses</span><strong>—</strong></div>
<div class="stat"><span>Audit requests</span><strong>—</strong></div>
<div class="stat"><span>Audit events</span><strong>—</strong></div>
</div>

<section>
<h2>Register a device</h2>
<form id="deviceForm" class="row">
<input name="device_uid" placeholder="Unique device ID" required maxlength="160">
<input name="label" placeholder="Device label" maxlength="160">
<button type="submit">Register device</button>
</form>
<p class="note">Keep the device ID unique. The credential is shown only once; do not share it.</p>
<div id="tokenBox">
<strong>Device credential — shown once</strong>
<p id="tokenText"></p>
<button type="button" id="copyToken">Copy credential</button>
<button type="button" class="secondary" id="hideToken">Hide</button>
</div>
</section>

<section>
<div class="row" style="justify-content:space-between">
<h2>Devices</h2><button id="refresh">Refresh</button>
</div>
<div class="wrap">
<table>
<thead><tr><th>Device ID</th><th>Label</th><th>Status</th><th>Last seen</th><th>Connection</th></tr></thead>
<tbody id="devices"><tr><td colspan="5">Loading…</td></tr></tbody>
</table>
</div>
</section>

<section>
<h2>Feature controls</h2>
<div class="wrap">
<table>
<thead><tr><th>Feature</th><th>State</th><th>Action</th></tr></thead>
<tbody id="features"><tr><td colspan="3">Loading…</td></tr></tbody>
</table>
</div>
</section>
<p class="note">This dashboard requires an administrator session. Do not expose it to the public internet until CSRF protection, login throttling, secure cookie settings and deployment security are addressed.</p>
</main>
<script>
const $ = id => document.getElementById(id);
function message(text){ $('message').textContent = text || ''; }
async function api(path, options={}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: {'Content-Type':'application/json', ...(options.headers||{})},
    ...options
  });
  const type = response.headers.get('content-type') || '';
  const data = type.includes('application/json') ? await response.json() : null;
  if (response.redirected && response.url.includes('/auth/login')) {
    location.href = '/auth/login';
    throw new Error('Administrator login required.');
  }
  if (!response.ok) throw new Error((data && (data.error || data.message)) || ('HTTP ' + response.status));
  return data;
}
function cell(row, value, className=''){
  const td = document.createElement('td');
  td.textContent = value == null || value === '' ? '—' : String(value);
  if(className) td.className = className;
  row.appendChild(td);
  return td;
}
async function loadOverview(){
  const data = await api('/api/dashboard-summary');
  const values = ['devices','surveys','survey_responses','audit_requests','audit_events'];
  $('stats').replaceChildren();
  for(const key of values){
    const box = document.createElement('div'); box.className='stat';
    const label = document.createElement('span'); label.textContent=key.replaceAll('_',' ');
    const number = document.createElement('strong'); number.textContent=String(data.counts[key] ?? 0);
    box.append(label,number); $('stats').appendChild(box);
  }
}
async function loadDevices(){
  const data = await api('/devices');
  const body = $('devices'); body.replaceChildren();
  if(!data.length){const tr=document.createElement('tr');cell(tr,'No devices registered.');body.appendChild(tr);return;}
  for(const d of data){
    const tr=document.createElement('tr');
    cell(tr,d.device_uid); cell(tr,d.label);
    cell(tr,d.connection_status,d.connection_status==='online'?'badge online':'badge offline');
    cell(tr,d.last_seen);
    const td=document.createElement('td');
    const btn=document.createElement('button');
    btn.textContent=d.enabled ? 'Disconnect' : 'Reconnect';
    btn.className=d.enabled ? 'secondary' : '';
    btn.addEventListener('click',async()=>{
      btn.disabled=true;
      try{
        await api('/admin/devices/'+encodeURIComponent(d.device_uid)+'/connection',{
          method:'POST',body:JSON.stringify({enabled:!Boolean(d.enabled)})
        });
        message('Connection setting updated for '+d.device_uid);
        await refreshAll();
      }catch(e){message(e.message);}finally{btn.disabled=false;}
    });
    td.appendChild(btn);tr.appendChild(td);body.appendChild(tr);
  }
}
async function loadFeatures(){
  const data=await api('/admin/features');
  const body=$('features');body.replaceChildren();
  if(!data.length){const tr=document.createElement('tr');cell(tr,'No feature flags found.');body.appendChild(tr);return;}
  for(const f of data){
    const tr=document.createElement('tr');
    cell(tr,f.name);cell(tr,f.enabled?'Enabled':'Disabled',f.enabled?'online':'offline');
    const td=document.createElement('td');const btn=document.createElement('button');
    btn.textContent=f.enabled?'Disable':'Enable';btn.className=f.enabled?'secondary':'';
    btn.addEventListener('click',async()=>{
      btn.disabled=true;
      try{
        await api('/admin/features/'+encodeURIComponent(f.name),{
          method:'POST',body:JSON.stringify({enabled:!Boolean(f.enabled)})
        });
        message('Feature updated: '+f.name);await refreshAll();
      }catch(e){message(e.message);}finally{btn.disabled=false;}
    });
    td.appendChild(btn);tr.appendChild(td);body.appendChild(tr);
  }
}
async function refreshAll(){
  try{await Promise.all([loadOverview(),loadDevices(),loadFeatures()]);}
  catch(e){message('Dashboard error: '+e.message);}
}
$('deviceForm').addEventListener('submit',async e=>{
  e.preventDefault();message('');
  const form=new FormData(e.target);
  try{
    const data=await api('/devices',{method:'POST',body:JSON.stringify({
      device_uid:String(form.get('device_uid')||'').trim(),
      label:String(form.get('label')||'').trim()
    })});
    $('tokenText').textContent=data.token_once;
    $('tokenBox').style.display='block';
    e.target.reset();
    message('Device registered. Save its credential securely now; it will not be shown again.');
    await refreshAll();
  }catch(err){message('Registration failed: '+err.message);}
});
$('copyToken').addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText($('tokenText').textContent);message('Credential copied. Store it securely.');}
  catch(e){message('Automatic copy unavailable. Select and copy the credential manually.');}
});
$('hideToken').addEventListener('click',()=>{$('tokenText').textContent='';$('tokenBox').style.display='none';});
$('refresh').addEventListener('click',refreshAll);
refreshAll();
</script>
</body>
</html>
"""

@bp.get("/")
@require_admin
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@bp.get("/api/dashboard-summary")
@require_admin
def dashboard_summary():
    db = connect()
    counts = {}
    for table in (
        "devices",
        "surveys",
        "survey_responses",
        "audit_requests",
        "audit_events",
    ):
        counts[table] = db.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
    return {"app": "Zentrix Device Connect", "counts": counts}
