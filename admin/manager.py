from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional


RUNTIME_DIR = Path("synapseflow_data")
USERS_FILE = RUNTIME_DIR / "admin_users.json"


@dataclass
class User:
    username: str
    role: str = "user"  # "admin" | "user"
    active: bool = True
    note: str = ""


def _ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def load_users() -> Dict[str, User]:
    _ensure_runtime_dir()
    if not USERS_FILE.exists():
        return {}
    with USERS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    users: Dict[str, User] = {}
    for username, record in data.items():
        users[username] = User(
            username=username,
            role=record.get("role", "user"),
            active=bool(record.get("active", True)),
            note=record.get("note", ""),
        )
    return users


def save_users(users: Dict[str, User]) -> None:
    _ensure_runtime_dir()
    to_dump = {u.username: asdict(u) for u in users.values()}
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(to_dump, f, indent=2, ensure_ascii=False)


def add_user(username: str, role: str = "user", active: bool = True, note: str = "") -> User:
    users = load_users()
    if username in users:
        raise ValueError("User already exists")
    if role not in {"admin", "user"}:
        raise ValueError("Invalid role")
    user = User(username=username, role=role, active=active, note=note)
    users[username] = user
    save_users(users)
    return user


def update_user(username: str, *, role: Optional[str] = None, active: Optional[bool] = None, note: Optional[str] = None) -> User:
    users = load_users()
    if username not in users:
        raise KeyError("User not found")
    user = users[username]
    if role is not None:
        if role not in {"admin", "user"}:
            raise ValueError("Invalid role")
        user.role = role
    if active is not None:
        user.active = bool(active)
    if note is not None:
        user.note = note
    users[username] = user
    save_users(users)
    return user


def remove_user(username: str) -> None:
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)


def list_users() -> List[User]:
    return list(load_users().values())

