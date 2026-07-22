from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        password_hash = current_app.config["ADMIN_PASSWORD_HASH"]
        if password_hash and check_password_hash(password_hash, password):
            session.permanent = True
            session["is_admin"] = True
            next_url = request.args.get("next") or url_for("admin.dashboard")
            return redirect(next_url)
        flash("Falsches Passwort.", "error")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
