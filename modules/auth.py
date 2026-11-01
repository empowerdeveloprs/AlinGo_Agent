from flask import Blueprint, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from .db import connect
from .security import require_admin

bp = Blueprint("auth", __name__, url_prefix="/auth")
LOGIN_HTML = '''<!doctype html><meta charset="utf-8"><title>Zentrix Login</title>
<h1>Zentrix Device Connect</h1>{% for m in get_flashed_messages() %}<p>{{m}}</p>{% endfor %}
<form method="post"><label>Username <input name="username" required></label>
<label>Password <input type="password" name="password" required></label><button>Login</button></form>'''

@bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        row = connect().execute("SELECT * FROM admins WHERE username=?", (request.form.get("username",""),)).fetchone()
        if row and check_password_hash(row["password_hash"], request.form.get("password","")):
            session.clear()
            session["admin_username"] = row["username"]
            return redirect(url_for("dashboard"))
        flash("Login failed")
    return render_template_string(LOGIN_HTML)

@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
