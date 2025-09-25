from __future__ import annotations

import os
from functools import wraps
from typing import Callable, Optional

from flask import Flask, redirect, render_template, request, session, url_for, flash

from admin.manager import add_user, list_users, remove_user, update_user


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="admin/templates",
        static_folder=None,
    )

    app.config["SECRET_KEY"] = os.getenv("ADMIN_SECRET", "dev-secret")
    app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "admin")
    app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "admin")

    def login_required(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect(url_for("login"))
            return fn(*args, **kwargs)

        return wrapper

    @app.get("/")
    @login_required
    def index():
        users = list_users()
        return render_template("users.html", users=users)

    @app.get("/login")
    def login():
        return render_template("login.html")

    @app.post("/login")
    def do_login():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == app.config["ADMIN_USERNAME"] and password == app.config["ADMIN_PASSWORD"]:
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("Invalid credentials", "error")
        return redirect(url_for("login"))

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.post("/users")
    @login_required
    def create_user():
        username = request.form.get("username", "").strip()
        role = request.form.get("role", "user")
        note = request.form.get("note", "").strip()
        if not username:
            flash("Username required", "error")
            return redirect(url_for("index"))
        try:
            add_user(username=username, role=role, note=note)
            flash("User added", "success")
        except Exception as e:  # keep simple for UI
            flash(str(e), "error")
        return redirect(url_for("index"))

    @app.post("/users/<username>/delete")
    @login_required
    def delete_user(username: str):
        remove_user(username)
        flash("User removed", "success")
        return redirect(url_for("index"))

    @app.post("/users/<username>/toggle")
    @login_required
    def toggle_user(username: str):
        active = request.form.get("active") == "on"
        role = request.form.get("role")
        note = request.form.get("note", "").strip()
        try:
            update_user(username, role=role, active=active, note=note)
            flash("User updated", "success")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("index"))

    return app


def main() -> None:
    app = create_app()
    host = os.getenv("ADMIN_HOST", "127.0.0.1")
    port = int(os.getenv("ADMIN_PORT", "5050"))
    # Never enable debug mode in production - security vulnerability
    debug_mode = os.getenv("ADMIN_DEBUG", "0") in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug_mode)


if __name__ == "__main__":
    main()

