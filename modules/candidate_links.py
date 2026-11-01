import json
import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, render_template_string
from .db import connect
from .security import require_admin, new_token, hash_token
from .audit_log import record

bp = Blueprint("candidate_links", __name__, url_prefix="/candidate")
CONSENT_VERSION = "sop-1"

SOP_HTML = """<!doctype html>
<html lang="ur" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zentrix — معلومات اور رضامندی</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:auto;padding:18px;line-height:1.8;color:#172033}
section{border:1px solid #d7deea;border-radius:12px;padding:16px;margin:14px 0}
button{padding:12px 18px;border:0;border-radius:8px;background:#174a86;color:white;font:inherit}
button:disabled{opacity:.5} .warn{color:#9a3412}
</style></head>
<body>
<h1>Zentrix — سروے سے پہلے معلومات</h1>
<section>
<h2>1۔ مقصد</h2>
<p>یہ صفحہ امیدوار کو سروے کا طریقۂ کار اور معلومات کے استعمال سے آگاہ کرنے کے لیے ہے۔ سروے یا امداد کی منظوری اس صفحے سے ضمانت شدہ نہیں۔</p>
<h2>2۔ معلومات اور رازداری</h2>
<p>صرف وہ معلومات جمع ہونی چاہییں جو سروے کے واضح مقصد کے لیے ضروری ہوں۔ جمع شدہ جوابات مجاز منتظمین دیکھ سکیں گے۔ لنک ذاتی ہے؛ اسے کسی دوسرے شخص سے شیئر نہ کریں۔</p>
<h2>3۔ براؤزر کی اجازتیں</h2>
<p>اگر مقام یا کیمرہ ضروری قرار دیا گیا ہو تو براؤزر الگ اجازت مانگے گا۔ اجازت دینے سے پہلے براؤزر کی درخواست پڑھیں۔ ویب صفحہ فون کی پوری اسٹوریج یا تمام Contacts تک عمومی رسائی حاصل نہیں کر سکتا۔ فائل درکار ہو تو آپ خود فائل منتخب کریں گے۔</p>
<h2>4۔ رضامندی اور اختیار</h2>
<p>آگے بڑھنے سے پہلے آپ کو معلومات پڑھ کر رضامندی دینی ہوگی۔ رضامندی نہ دینے پر سروے نہیں کھلے گا۔ آپ صفحہ بند کر سکتے ہیں۔</p>
<p class="warn">اگر پروگرام، ادارے یا مالی امداد کی شرائط کی تصدیق نہ ہوئی ہو تو کسی رقم کو منظور شدہ امداد نہ سمجھیں۔</p>
</section>
<form method="post" action="{{ url_for('candidate_links.consent', token=token) }}">
<label><input type="checkbox" name="agree" value="yes" required> میں نے اوپر کی معلومات پڑھ لی ہیں اور سروے کے لیے رضامندی دیتا/دیتی ہوں۔</label>
<p><button type="submit">رضامندی کے بعد آگے بڑھیں</button></p>
</form>
</body></html>"""

BLOCKED_HTML = """<!doctype html><html lang="ur" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>سروے دستیاب نہیں</title><body style="font-family:system-ui;max-width:700px;margin:auto;padding:20px">
<h1>سروے ابھی دستیاب نہیں</h1><p>{{ message }}</p></body></html>"""

PERMISSION_HTML = """<!doctype html><html lang="ur" dir="rtl">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>اجازتوں کی جانچ</title>
<body style="font-family:system-ui;max-width:700px;margin:auto;padding:20px;line-height:1.8">
<h1>مطلوبہ اجازتوں کی جانچ</h1>
<p>اس نمونے میں مقام اور کیمرہ دونوں ضروری ہیں۔ ہر اجازت براؤزر الگ مانگے گا۔ انکار ہونے پر سروے نہیں کھلے گا۔</p>
<p id="status">اجازتوں کی جانچ کے لیے بٹن دبائیں۔</p>
<button id="check">اجازتیں چیک کریں</button>
<form id="continue" method="post" action="{{ url_for('candidate_links.permission_result', token=token) }}">
<input type="hidden" name="report" id="report">
<button type="submit" id="submit" disabled>اجازتوں کے بعد سروے کھولیں</button>
</form>
<script>
const statusEl=document.getElementById('status');
const submitEl=document.getElementById('submit');
const reportEl=document.getElementById('report');
document.getElementById('check').addEventListener('click',async()=>{
  submitEl.disabled=true;
  const result={location:false,camera:false};
  try {
    if (!window.isSecureContext) throw new Error('HTTPS محفوظ کنکشن درکار ہے۔');
    if (!navigator.geolocation) throw new Error('مقام کی سہولت دستیاب نہیں۔');
    await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(
      ()=>{result.location=true;resolve();},reject,{enableHighAccuracy:false,timeout:10000,maximumAge:0}));
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia)
      throw new Error('کیمرہ کی سہولت دستیاب نہیں۔');
    const stream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});
    result.camera=true;
    stream.getTracks().forEach(track=>track.stop());
    reportEl.value=JSON.stringify(result);
    submitEl.disabled=false;
    statusEl.textContent='مقام اور کیمرہ دونوں کی اجازت مل گئی۔ اب آگے بڑھ سکتے ہیں۔';
  } catch(e) {
    reportEl.value=JSON.stringify(result);
    statusEl.textContent='اجازت مکمل نہیں ہوئی: '+(e.message||'اجازت مسترد یا دستیاب نہیں')+'. سروے نہیں کھلے گا۔';
  }
});
</script></body></html>"""

SURVEY_HTML = """<!doctype html><html lang="ur" dir="rtl">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>امیدوار سروے</title><body style="font-family:system-ui;max-width:700px;margin:auto;padding:20px;line-height:1.8">
<h1>امیدوار سروے</h1><p>یہ ابتدائی محفوظ نمونہ ہے۔ اپنے سروے کے اصل سوالات شامل ہونے تک ذاتی یا حساس معلومات درج نہ کریں۔</p>
<form method="post" action="{{ url_for('candidate_links.submit_survey', token=token) }}">
<label>امیدوار کا بیان<br><textarea name="statement" maxlength="4000" rows="6" required></textarea></label><br>
<button type="submit">جواب جمع کریں</button></form></body></html>"""

def get_candidate(token):
    if not token or len(token) > 200:
        return None
    row = connect().execute(
        "SELECT * FROM candidate_links WHERE token_hash=?",
        (hash_token(token),)
    ).fetchone()
    if not row or row["revoked"]:
        return None
    try:
        expiry = datetime.fromisoformat(row["expires_at"])
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc):
            return None
    except (ValueError, TypeError):
        return None
    return row

@bp.post("/admin/links")
@require_admin
def create_link():
    data = request.get_json(silent=True) or {}
    label = str(data.get("candidate_label", "")).strip()
    try:
        hours = int(data.get("valid_hours", 72))
    except (ValueError, TypeError):
        return jsonify(error="valid_hours_must_be_integer"), 400
    if not label or len(label) > 160:
        return jsonify(error="candidate_label_required_max_160"), 400
    if not 1 <= hours <= 720:
        return jsonify(error="valid_hours_must_be_1_to_720"), 400
    token = new_token()
    expiry = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    db = connect()
    cur = db.execute(
        "INSERT INTO candidate_links(candidate_label,token_hash,expires_at,created_by) VALUES(?,?,?,?)",
        (label, hash_token(token), expiry, str(session_username()))
    )
    db.commit()
    record("admin", "candidate_link_created", str(cur.lastrowid), {"expires_at": expiry})
    return jsonify(
        id=cur.lastrowid,
        candidate_label=label,
        expires_at=expiry,
        link_path=f"/candidate/{token}",
        token_once=token,
        note="Save this link securely; the token is not shown again."
    ), 201

def session_username():
    from flask import session
    return session.get("admin_username", "admin")

@bp.get("/admin/links")
@require_admin
def list_links():
    rows = connect().execute(
        "SELECT id,candidate_label,expires_at,revoked,consented_at,consent_version,created_by,created_at "
        "FROM candidate_links ORDER BY id DESC"
    ).fetchall()
    return jsonify([dict(row) for row in rows])

@bp.post("/admin/links/<int:link_id>/revoke")
@require_admin
def revoke_link(link_id):
    db = connect()
    cur = db.execute("UPDATE candidate_links SET revoked=1 WHERE id=?", (link_id,))
    db.commit()
    if not cur.rowcount:
        return jsonify(error="link_not_found"), 404
    record("admin", "candidate_link_revoked", str(link_id), {})
    return jsonify(status="revoked")

@bp.get("/<token>")
def show_sop(token):
    row = get_candidate(token)
    if not row:
        return render_template_string(BLOCKED_HTML, message="لنک غلط، ختم شدہ یا منسوخ ہو چکا ہے۔"), 410
    return render_template_string(SOP_HTML, token=token)

@bp.post("/<token>/consent")
def consent(token):
    row = get_candidate(token)
    if not row:
        return render_template_string(BLOCKED_HTML, message="لنک غلط، ختم شدہ یا منسوخ ہو چکا ہے۔"), 410
    if request.form.get("agree") != "yes":
        return render_template_string(BLOCKED_HTML, message="رضامندی کے بغیر سروے نہیں کھل سکتا۔"), 403
    db = connect()
    db.execute(
        "UPDATE candidate_links SET consented_at=CURRENT_TIMESTAMP,consent_version=? WHERE id=?",
        (CONSENT_VERSION, row["id"])
    )
    db.commit()
    record("candidate", "candidate_consent_given", str(row["id"]), {"version": CONSENT_VERSION})
    return render_template_string(PERMISSION_HTML, token=token)

@bp.post("/<token>/permissions")
def permission_result(token):
    row = get_candidate(token)
    if not row:
        return render_template_string(BLOCKED_HTML, message="لنک غلط، ختم شدہ یا منسوخ ہو چکا ہے۔"), 410
    if not row["consented_at"]:
        return render_template_string(BLOCKED_HTML, message="پہلے رضامندی ضروری ہے۔"), 403
    raw = request.form.get("report", "")
    try:
        report_data = json.loads(raw)
    except (ValueError, TypeError):
        report_data = None
    if not isinstance(report_data, dict) or report_data.get("location") is not True or report_data.get("camera") is not True:
        return render_template_string(BLOCKED_HTML, message="مقام اور کیمرہ دونوں کی مطلوبہ اجازتوں کی تصدیق نہیں ہوئی۔"), 403
    # Client report browser-side evidence ہے، cryptographic proof نہیں۔
    db = connect()
    db.execute("UPDATE candidate_links SET permission_report_json=? WHERE id=?",
               (json.dumps(report_data), row["id"]))
    db.commit()
    return render_template_string(SURVEY_HTML, token=token)

@bp.post("/<token>/submit")
def submit_survey(token):
    row = get_candidate(token)
    if not row:
        return jsonify(error="invalid_expired_or_revoked_link"), 410
    if not row["consented_at"] or not row["permission_report_json"]:
        return jsonify(error="consent_and_permissions_required"), 403

    statement = request.form.get("statement", "").strip()
    if not statement or len(statement) > 4000:
        return jsonify(error="statement_required_max_4000"), 400

    db = connect()
    try:
        # Atomic guard: only the first submission may set survey_json.
        cursor = db.execute(
            """UPDATE candidate_links
               SET survey_json=?
               WHERE id=? AND survey_json IS NULL""",
            (
                json.dumps({"statement": statement}, ensure_ascii=False),
                row["id"],
            ),
        )
        db.commit()

        if cursor.rowcount != 1:
            return jsonify(error="submission_already_completed"), 409

        record("candidate", "candidate_survey_submitted", str(row["id"]), {})
        return render_template_string(
            BLOCKED_HTML,
            message="آپ کے جواب محفوظ کر لیے گئے ہیں۔",
        ), 200
    finally:
        db.close()
