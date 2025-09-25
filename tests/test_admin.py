from __future__ import annotations

import os
from pathlib import Path

import pytest

from admin_server import create_app
from admin import manager


def test_manager_crud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Redirect storage to temp path
    users_file = tmp_path / "admin_users.json"
    monkeypatch.setattr(manager, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(manager, "USERS_FILE", users_file)

    # Initially empty
    assert manager.list_users() == []

    # Add
    u = manager.add_user("alice", role="admin", note="owner")
    assert u.username == "alice" and u.role == "admin" and u.active is True

    # Update
    u2 = manager.update_user("alice", role="user", active=False, note="disabled")
    assert u2.role == "user" and u2.active is False and u2.note == "disabled"

    # Remove
    manager.remove_user("alice")
    assert manager.list_users() == []


def test_admin_login_flow(monkeypatch: pytest.MonkeyPatch):
    # Configure app credentials
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("ADMIN_SECRET", "test-secret")

    app = create_app()
    client = app.test_client()

    # Cannot access index without login
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.location

    # Wrong login
    r = client.post("/login", data={"username": "admin", "password": "nope"}, follow_redirects=True)
    assert b"Invalid credentials" in r.data

    # Correct login
    r = client.post("/login", data={"username": "admin", "password": "secret"}, follow_redirects=True)
    assert r.status_code == 200
    assert b"Users" in r.data

