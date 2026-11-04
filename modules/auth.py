from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import check_password_hash
from .db import connect
from .security import require_admin

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        row = connect().execute("SELECT * FROM admins WHERE username=?", (request.form.get("username",""),)).fetchone()
        if row and check_password_hash(row["password_hash"], request.form.get("password","")):
            session.clear()
            session["admin_username"] = row["username"]
            if request.headers.get("HX-Request"):
                resp = make_response("", 204)
                resp.headers["HX-Redirect"] = url_for("dashboard")
                return resp
            return redirect(url_for("dashboard"))
        flash("Login failed")
    return render_template("login.html")

@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
