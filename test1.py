#!/usr/bin/env python3
import requests, json, os
from datetime import datetime

BASE_URL = os.environ.get("DAYLE_SERVER", "http://127.0.0.1:8081")

def send_reply(incoming, contact="Tester"):
    r = requests.post(f"{BASE_URL}/reply", json={"incoming": incoming, "contact": contact}, timeout=30)
    r.raise_for_status()
    return r.json()

def send_feedback(incoming, draft, final, contact="Tester", accepted=True, edited=False):
    payload = {
        "ts": datetime.utcnow().isoformat()+"Z",
        "incoming": incoming, "contact": contact,
        "draft": draft, "final": final,
        "accepted": accepted, "edited": edited
    }
    r = requests.post(f"{BASE_URL}/feedback", json=payload, timeout=30)
    r.raise_for_status(); return r.json()

def main():
    print(f"Server: {BASE_URL}")
    while True:
        msg = input("Incoming (blank to quit): ").strip()
        if not msg: break
        res = send_reply(msg)
        draft = res.get("draft") or res.get("reply") or ""
        print("\n--- DRAFT ---\n"+draft)
        choice = input("\n[A]ccept / [E]dit / [R]eject? ").lower().strip()
        if choice == "a":
            print(send_feedback(msg, draft, draft, accepted=True, edited=False))
        elif choice == "e":
            final = input("Your edit: ").strip()
            print(send_feedback(msg, draft, final, accepted=True, edited=True))
        else:
            print(send_feedback(msg, draft, "", accepted=False, edited=False))
        print()
if __name__ == "__main__":
    main()
