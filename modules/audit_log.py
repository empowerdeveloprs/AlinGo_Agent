import json
from .db import connect

def record(actor, action, target="", details=None):
    db = connect()
    db.execute("INSERT INTO audit_events(actor, action, target, details_json) VALUES(?,?,?,?)",
               (actor, action, target, json.dumps(details or {}, ensure_ascii=False)))
    db.commit()
