import json
from flask import Blueprint, request, jsonify
from .db import connect
from .security import require_admin, require_device_token
from .audit_log import record

bp = Blueprint("surveys", __name__, url_prefix="/api/v1")

def feature_enabled(name):
    row = connect().execute("SELECT enabled FROM feature_flags WHERE name=?", (name,)).fetchone()
    return bool(row and row["enabled"])

@bp.get("/surveys")
@require_device_token
def assigned_surveys():
    db = connect()
    if not feature_enabled("surveys"):
        return jsonify({"error":"feature_disabled"}), 403
    rows = db.execute("SELECT id,title,description,schema_json FROM surveys WHERE enabled=1 ORDER BY id").fetchall()
    return jsonify([{"id":r["id"],"title":r["title"],"description":r["description"],"schema":json.loads(r["schema_json"])} for r in rows])

@bp.post("/surveys/<int:survey_id>/responses")
@require_device_token
def submit_response(survey_id):
    db = connect()
    if not feature_enabled("surveys"):
        return jsonify({"error":"feature_disabled"}), 403
    if not db.execute("SELECT id FROM surveys WHERE id=? AND enabled=1",(survey_id,)).fetchone():
        return jsonify({"error":"survey_not_found"}), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error":"json_object_required"}), 400
    db.execute("INSERT INTO survey_responses(survey_id,device_uid,response_json) VALUES(?,?,?)",
               (survey_id,request.device_uid,json.dumps(data,ensure_ascii=False)))
    db.commit()
    record(request.device_uid,"survey_response_submitted",str(survey_id),{})
    return jsonify({"status":"saved"}), 201

@bp.route("/admin/surveys", methods=["GET","POST"])
@require_admin
def admin_surveys():
    db = connect()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        title = str(data.get("title","")).strip()
        schema = data.get("schema",[])
        if not title or not isinstance(schema,list):
            return jsonify({"error":"title_and_schema_list_required"}), 400
        cur = db.execute("INSERT INTO surveys(title,description,schema_json) VALUES(?,?,?)",
                         (title,str(data.get("description","")),json.dumps(schema,ensure_ascii=False)))
        db.commit()
        record("admin","survey_created",str(cur.lastrowid),{"title":title})
        return jsonify({"id":cur.lastrowid}), 201
    rows = db.execute("SELECT * FROM surveys ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@bp.get("/admin/surveys/<int:survey_id>/responses")
@require_admin
def response_report(survey_id):
    rows = connect().execute("SELECT * FROM survey_responses WHERE survey_id=? ORDER BY id DESC",(survey_id,)).fetchall()
    return jsonify([dict(r) for r in rows])
