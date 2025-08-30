#!/usr/bin/env python3
"""
Dayle SMS AI test client

Features:
- Local: call /reply, /feedback, profile get/set, interactive REPL
- Twilio: send SMS; webhook with auto-reply and optional REST send
- KDE Connect: list devices, send SMS, basic notification watcher
- Messenger: webhook with verify/signature check; optional send via Graph API

Env vars:
- DAYLE_SERVER: base URL of the local server (default http://127.0.0.1:8081)
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM: credentials for Twilio
- FB_PAGE_TOKEN: Facebook Page access token (send API)
- FB_VERIFY_TOKEN: Token to validate webhook subscription
- FB_APP_SECRET: App secret for X-Hub-Signature-256 verification (recommended)

Security & Error Handling:
- Strict timeouts, argument validation, safe defaults, clear exit codes.
- Webhooks validate tokens and signatures when provided.

Note: KDE receive is limited; Messenger requires public HTTPS webhook.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

import requests

BASE_URL = os.environ.get("DAYLE_SERVER", "http://127.0.0.1:8081").rstrip("/")
DEFAULT_TIMEOUT = (5, 60)  # (connect, read)


class ClientError(RuntimeError):
    pass


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    fmt = os.environ.get("LOG_FORMAT", "text")
    if fmt == "json":
        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                base = {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "name": record.name,
                    "msg": record.getMessage(),
                }
                if record.exc_info:
                    base["exc"] = self.formatException(record.exc_info)
                return json.dumps(base, ensure_ascii=False)
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


log = logging.getLogger("smsai.client")


# ---- Clients & Transports (class-based) ----
TRANSPORT_REGISTRY: Dict[str, Any] = {}


def register_transport(name: str):
    def deco(cls):
        TRANSPORT_REGISTRY[name] = cls
        return cls
    return deco
class LocalAPIClient:
    def __init__(self, base_url: str, timeout=DEFAULT_TIMEOUT):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def reply(self, incoming: str, contact: str = "Tester") -> Dict[str, Any]:
        try:
            r = requests.post(
                f"{self.base}/reply",
                json={"incoming": incoming, "contact": contact},
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("/reply failed", extra={"error": str(e)})
            raise ClientError(f"/reply request failed: {e}")

    def feedback(
        self,
        incoming: str,
        draft: str,
        final: str,
        contact: str = "Tester",
        accepted: bool = True,
        edited: bool = False,
    ) -> Dict[str, Any]:
        payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "incoming": incoming,
            "contact": contact,
            "draft": draft,
            "final": final,
            "accepted": accepted,
            "edited": edited,
        }
        try:
            r = requests.post(f"{self.base}/feedback", json=payload, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("/feedback failed", extra={"error": str(e)})
            raise ClientError(f"/feedback request failed: {e}")

    def get_profile(self) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.base}/profile", timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("/profile get failed", extra={"error": str(e)})
            raise ClientError(f"/profile get failed: {e}")

    def set_profile(self, update: Dict[str, Any]) -> Dict[str, Any]:
        try:
            r = requests.post(f"{self.base}/profile", json=update, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error("/profile set failed", extra={"error": str(e)})
            raise ClientError(f"/profile set failed: {e}")


LOCAL = LocalAPIClient(BASE_URL, DEFAULT_TIMEOUT)


def discover_transports() -> Dict[str, str]:
    """Best-effort load transports from plugins/transports/*.py"""
    import importlib.util
    import glob
    loaded = {}
    for path in glob.glob("plugins/transports/*.py"):
        name = path.replace("/", ".").rstrip(".py")
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            continue
        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            loaded[name] = "ok"
        except Exception as e:
            loaded[name] = f"error: {e}"
    return loaded


def pretty(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# ---- Local server helpers ----
def api_reply(incoming: str, contact: str = "Tester") -> Dict[str, Any]:
    return LOCAL.reply(incoming, contact)


def api_feedback(
    incoming: str,
    draft: str,
    final: str,
    contact: str = "Tester",
    accepted: bool = True,
    edited: bool = False,
) -> Dict[str, Any]:
    return LOCAL.feedback(incoming, draft, final, contact, accepted, edited)


def api_get_profile() -> Dict[str, Any]:
    return LOCAL.get_profile()


def api_set_profile(update: Dict[str, Any]) -> Dict[str, Any]:
    return LOCAL.set_profile(update)


# ---- Interactive REPL ----
def cmd_interactive(args: argparse.Namespace) -> None:
    print(f"Server: {BASE_URL}")
    while True:
        try:
            msg = input("Incoming (blank to quit): ").strip()
        except EOFError:
            break
        if not msg:
            break
        res = api_reply(msg, contact=args.contact)
        draft = (res.get("draft") or res.get("reply") or "").strip()
        print("\n--- DRAFT ---\n" + draft)
        choice = input("\n[A]ccept / [E]dit / [R]eject? ").lower().strip()
        if choice == "a":
            pretty(
                api_feedback(
                    incoming=msg, draft=draft, final=draft, contact=args.contact, accepted=True, edited=False
                )
            )
        elif choice == "e":
            final = input("Your edit: ").strip()
            pretty(
                api_feedback(
                    incoming=msg, draft=draft, final=final, contact=args.contact, accepted=True, edited=True
                )
            )
        else:
            pretty(
                api_feedback(
                    incoming=msg, draft=draft, final="", contact=args.contact, accepted=False, edited=False
                )
            )
        print()


# ---- Simple one-shot commands ----
def cmd_reply(args: argparse.Namespace) -> None:
    _validate_text(args.incoming)
    res = api_reply(args.incoming, contact=args.contact)
    pretty(res)


def cmd_feedback(args: argparse.Namespace) -> None:
    _validate_text(args.incoming)
    res = api_feedback(
        incoming=args.incoming,
        draft=args.draft,
        final=args.final,
        contact=args.contact,
        accepted=args.accepted,
        edited=args.edited,
    )
    pretty(res)


def cmd_profile(args: argparse.Namespace) -> None:
    if args.action == "get":
        pretty(api_get_profile())
    elif args.action == "set":
        update: Dict[str, Any] = {}
        if args.style_rules is not None:
            update["style_rules"] = args.style_rules
        if args.preferred_phrases is not None:
            update["preferred_phrases"] = [s.strip() for s in args.preferred_phrases.split(";") if s.strip()]
        if args.banned_words is not None:
            update["banned_words"] = [s.strip() for s in args.banned_words.split(",") if s.strip()]
        if not update:
            print("Nothing to update. Use --style-rules/--preferred-phrases/--banned-words.")
            return
        pretty(api_set_profile(update))


# ---- Twilio integration ----
def _twilio_client():
    try:
        from twilio.rest import Client  # type: ignore
    except Exception as e:
        print("Twilio SDK not installed. Install with: pip install twilio", file=sys.stderr)
        raise
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    tok = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not tok:
        print("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in env.", file=sys.stderr)
        sys.exit(2)
    return Client(sid, tok)


def cmd_twilio_send(args: argparse.Namespace) -> None:
    from_num = args.from_number or os.environ.get("TWILIO_FROM")
    if not from_num:
        print("Provide --from or set TWILIO_FROM.", file=sys.stderr)
        sys.exit(2)
    try:
        res = TwilioTransport(from_num).send_sms(args.to, args.text)
        pretty(res)
    except Exception as e:
        print(f"Twilio send failed: {e}", file=sys.stderr)
        sys.exit(1)


@register_transport("twilio")
class TwilioTransport:
    def __init__(self, from_number: Optional[str]):
        self.from_number = from_number or os.environ.get("TWILIO_FROM")

    def send_sms(self, to: str, text: str) -> Dict[str, Any]:
        _validate_phone(to); _validate_text(text)
        client = _twilio_client()
        msg = client.messages.create(from_=self.from_number, to=to, body=text)
        return {"sid": msg.sid, "status": msg.status}

    def create_app(self, auto: bool):
        try:
            from flask import Flask, request, Response
        except Exception:
            print("Flask not installed. pip install flask", file=sys.stderr)
            sys.exit(2)

        app = Flask(__name__)

        @app.post("/sms")
        def sms():  # type: ignore
            from_number_in = request.form.get("From", "")
            body = request.form.get("Body", "")
            contact = request.form.get("ProfileName") or from_number_in
            log.info("twilio webhook received", extra={"from": from_number_in})
            try:
                res = api_reply(body, contact=contact)
                draft = (res.get("draft") or res.get("reply") or "").strip()
            except Exception as e:
                draft = "(error generating reply)"
                log.error("twilio draft failed", extra={"error": str(e)})

            if auto and self.from_number:
                try:
                    client = _twilio_client()
                    client.messages.create(from_=self.from_number, to=from_number_in, body=draft)
                except Exception as e:
                    log.error("twilio auto-send failed", extra={"error": str(e)})

            # Return TwiML so Twilio can optionally send as the webhook response
            twiml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Response><Message>{_xml_escape(draft)}</Message></Response>"""
            return Response(twiml, mimetype="application/xml")

        return app


def create_twilio_app(from_number: Optional[str], auto: bool):
    return TwilioTransport(from_number).create_app(auto)


def create_twilio_app_from_env():
    auto = os.environ.get("AUTO_REPLY", "").lower() in ("1", "true", "yes")
    return TwilioTransport(os.environ.get("TWILIO_FROM")).create_app(auto)


def cmd_twilio_webhook(args: argparse.Namespace) -> None:
    app = create_twilio_app(from_number=args.from_number or os.environ.get("TWILIO_FROM"), auto=bool(args.auto))
    log.info("Starting Twilio webhook", extra={"host": args.host, "port": args.port})
    if not args.public_note_shown:
        print("Note: expose this endpoint publicly (e.g., via ngrok) and configure Twilio Messaging webhook.")
    app.run(host=args.host, port=args.port)


# ---- KDE Connect integration ----
def _kde_cmd(*argv: str) -> str:
    import subprocess

    try:
        out = subprocess.check_output(["kdeconnect-cli", *argv], text=True)
        return out
    except FileNotFoundError:
        print("kdeconnect-cli not found. Install KDE Connect and ensure CLI is on PATH.", file=sys.stderr)
        sys.exit(2)


def cmd_kde_devices(_: argparse.Namespace) -> None:
    out = _kde_cmd("--list-devices")
    print(out)


def cmd_kde_send(args: argparse.Namespace) -> None:
    if not args.device_id:
        print("--device-id required. Use `kde devices` to list.", file=sys.stderr)
        sys.exit(2)
    _validate_phone(args.to)
    _validate_text(args.text)
    _ = _kde_cmd("--device", args.device_id, "--send-sms", args.text, "--destination", args.to)
    print("Sent via KDE Connect.")


def cmd_kde_watch(args: argparse.Namespace) -> None:
    # Best-effort notification poller; prints notifications that may contain SMS
    # Future: parse sender/number and auto-reply via send-sms.
    last_dump = ""
    try:
        while True:
            out = _kde_cmd("--device", args.device_id, "--list-notifications")
            if out != last_dump:
                os.system("clear")
                print(time.strftime("[%H:%M:%S] Notifications:"))
                print(out)
                last_dump = out
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


# ---- Validation & helpers ----
def _validate_phone(num: str) -> None:
    if not num or not isinstance(num, str):
        print("Phone number is required.", file=sys.stderr)
        sys.exit(2)
    s = num.strip()
    # Very simple E.164-ish validation
    digits = s.replace(" ", "").replace("-", "")
    if not digits.startswith("+") or not digits[1:].isdigit() or len(digits) < 8:
        print("Phone must be E.164 like +15551234567.", file=sys.stderr)
        sys.exit(2)


def _validate_text(text: str) -> None:
    if not isinstance(text, str) or not text.strip():
        print("Text cannot be empty.", file=sys.stderr)
        sys.exit(2)
    if len(text) > 2000:
        print("Text too long (>2000 chars).", file=sys.stderr)
        sys.exit(2)


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ---- Messenger integration ----
def _fb_send(psid: str, text: str, page_token: Optional[str] = None) -> Dict[str, Any]:
    _validate_text(text)
    if not psid:
        raise ClientError("Missing PSID")
    token = page_token or os.environ.get("FB_PAGE_TOKEN")
    if not token:
        raise ClientError("FB_PAGE_TOKEN not set")
    url = "https://graph.facebook.com/v19.0/me/messages"
    try:
        r = requests.post(
            url,
            params={"access_token": token},
            json={"recipient": {"id": psid}, "messaging_type": "RESPONSE", "message": {"text": text}},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise ClientError(f"Facebook send failed: {e}")


def _verify_fb_sig(app_secret: str, payload: bytes, header_sig: Optional[str]) -> bool:
    import hmac, hashlib

    if not header_sig or not header_sig.startswith("sha256="):
        return False
    try:
        digest = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        provided = header_sig.split("=", 1)[1]
        return hmac.compare_digest(digest, provided)
    except Exception:
        return False


def cmd_msgr_send(args: argparse.Namespace) -> None:
    try:
        res = _fb_send(args.psid, args.text, page_token=args.page_token)
    except ClientError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    pretty(res)


@register_transport("messenger")
class MessengerTransport:
    def __init__(self, verify_token: Optional[str], app_secret: Optional[str], page_token: Optional[str]):
        self.verify_token = verify_token or os.environ.get("FB_VERIFY_TOKEN")
        self.app_secret = app_secret or os.environ.get("FB_APP_SECRET")
        self.page_token = page_token or os.environ.get("FB_PAGE_TOKEN")

    def create_app(self, auto: bool):
        try:
            from flask import Flask, request, Response
        except Exception:
            print("Flask not installed. pip install flask", file=sys.stderr)
            sys.exit(2)

        app = Flask(__name__)

        @app.get("/webhook")
        def verify():  # type: ignore
            mode = request.args.get("hub.mode")
            token = request.args.get("hub.verify_token")
            challenge = request.args.get("hub.challenge")
            ok = mode == "subscribe" and challenge and self.verify_token and token == self.verify_token
            log.info("msgr verify", extra={"ok": bool(ok)})
            if ok:
                return Response(challenge, status=200)
            return Response("forbidden", status=403)

        @app.post("/webhook")
        def receive():  # type: ignore
            # Signature validation
            if self.app_secret:
                sig = request.headers.get("X-Hub-Signature-256")
                body = request.get_data() or b""
                if not _verify_fb_sig(self.app_secret, body, sig):
                    log.warning("msgr invalid signature")
                    return Response("invalid signature", status=403)
            data = request.get_json(silent=True) or {}
            try:
                for entry in data.get("entry", []):
                    for m in entry.get("messaging", []):
                        sender = (m.get("sender") or {}).get("id")
                        msg = (m.get("message") or {}).get("text")
                        if not sender or not msg:
                            continue
                        log.info("msgr message", extra={"sender": sender})
                        # Call local server for draft
                        try:
                            res = api_reply(msg, contact=f"fb:{sender}")
                            draft = (res.get("draft") or res.get("reply") or "").strip()
                        except Exception as e:
                            draft = "(error generating reply)"
                            log.error("msgr draft failed", extra={"error": str(e)})
                        if auto and self.page_token:
                            try:
                                _fb_send(sender, draft, page_token=self.page_token)
                            except Exception as e:
                                log.error("msgr send failed", extra={"error": str(e)})
            except Exception as e:
                log.error("msgr webhook error", extra={"error": str(e)})
            return Response("ok", status=200)

        return app


def create_messenger_app(verify_token: Optional[str], app_secret: Optional[str], page_token: Optional[str], auto: bool):
    return MessengerTransport(verify_token, app_secret, page_token).create_app(auto)


def create_messenger_app_from_env():
    auto = os.environ.get("AUTO_REPLY", "").lower() in ("1", "true", "yes")
    return MessengerTransport(None, None, None).create_app(auto)


def cmd_msgr_webhook(args: argparse.Namespace) -> None:
    app = create_messenger_app(
        verify_token=args.verify_token or os.environ.get("FB_VERIFY_TOKEN"),
        app_secret=args.app_secret or os.environ.get("FB_APP_SECRET"),
        page_token=args.page_token or os.environ.get("FB_PAGE_TOKEN"),
        auto=bool(args.auto),
    )
    log.info("Messenger webhook", extra={"host": args.host, "port": args.port})
    if not args.public_note_shown:
        print("Expose publicly via HTTPS and configure in Meta App settings.")
    app.run(host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Dayle SMS AI test client")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")
    sub = p.add_subparsers(dest="cmd", required=True)

    # interactive REPL
    i = sub.add_parser("interactive", help="Interactive test loop")
    i.add_argument("--contact", default="Tester")
    i.set_defaults(func=cmd_interactive)

    # one-shot reply
    r = sub.add_parser("reply", help="Call /reply and print result")
    r.add_argument("incoming")
    r.add_argument("--contact", default="Tester")
    r.set_defaults(func=cmd_reply)

    # feedback
    f = sub.add_parser("feedback", help="Send feedback to server")
    f.add_argument("incoming")
    f.add_argument("draft")
    f.add_argument("final")
    f.add_argument("--contact", default="Tester")
    f.add_argument("--accepted", action="store_true", default=True)
    f.add_argument("--edited", action="store_true", default=False)
    f.set_defaults(func=cmd_feedback)

    # profile get/set
    prof = sub.add_parser("profile", help="Get or set profile")
    prof_sub = prof.add_subparsers(dest="action", required=True)
    prof_get = prof_sub.add_parser("get", help="Get current profile")
    prof_get.set_defaults(func=cmd_profile)
    prof_set = prof_sub.add_parser("set", help="Update profile fields")
    prof_set.add_argument("--style-rules")
    prof_set.add_argument("--preferred-phrases", help="Semicolon-separated phrases")
    prof_set.add_argument("--banned-words", help="Comma-separated words")
    prof_set.set_defaults(func=cmd_profile)

    # Twilio
    tw = sub.add_parser("twilio", help="Twilio utilities")
    tw_sub = tw.add_subparsers(dest="tw_cmd", required=True)
    tw_send = tw_sub.add_parser("send", help="Send SMS via Twilio")
    tw_send.add_argument("--from", dest="from_number")
    tw_send.add_argument("--to", required=True)
    tw_send.add_argument("--text", required=True)
    tw_send.set_defaults(func=cmd_twilio_send)

    tw_hook = tw_sub.add_parser("webhook", help="Run Flask webhook to auto-reply")
    tw_hook.add_argument("--host", default="0.0.0.0")
    tw_hook.add_argument("--port", type=int, default=5005)
    tw_hook.add_argument("--from", dest="from_number")
    tw_hook.add_argument("--auto", action="store_true", help="Also send reply via REST API")
    tw_hook.add_argument("--public-note-shown", action="store_true")
    tw_hook.set_defaults(func=cmd_twilio_webhook)

    # KDE Connect
    kde = sub.add_parser("kde", help="KDE Connect utilities")
    kde_sub = kde.add_subparsers(dest="kde_cmd", required=True)
    kde_list = kde_sub.add_parser("devices", help="List devices")
    kde_list.set_defaults(func=cmd_kde_devices)

    kde_send = kde_sub.add_parser("send", help="Send SMS via KDE Connect")
    kde_send.add_argument("--device-id", required=True)
    kde_send.add_argument("--to", required=True)
    kde_send.add_argument("--text", required=True)
    kde_send.set_defaults(func=cmd_kde_send)

    kde_watch = kde_sub.add_parser("watch", help="Poll notifications (best-effort)")
    kde_watch.add_argument("--device-id", required=True)
    kde_watch.add_argument("--interval", type=float, default=5.0)
    kde_watch.set_defaults(func=cmd_kde_watch)

    # Messenger
    ms = sub.add_parser("messenger", help="Facebook Messenger utilities")
    ms_sub = ms.add_subparsers(dest="ms_cmd", required=True)

    ms_send = ms_sub.add_parser("send", help="Send message to PSID via Graph API")
    ms_send.add_argument("--psid", required=True)
    ms_send.add_argument("--text", required=True)
    ms_send.add_argument("--page-token", dest="page_token")
    ms_send.set_defaults(func=cmd_msgr_send)

    ms_hook = ms_sub.add_parser("webhook", help="Run webhook for Messenger platform")
    ms_hook.add_argument("--host", default="0.0.0.0")
    ms_hook.add_argument("--port", type=int, default=5006)
    ms_hook.add_argument("--verify-token", dest="verify_token")
    ms_hook.add_argument("--app-secret", dest="app_secret")
    ms_hook.add_argument("--page-token", dest="page_token")
    ms_hook.add_argument("--auto", action="store_true", help="Send reply via Graph API")
    ms_hook.add_argument("--public-note-shown", action="store_true")
    ms_hook.set_defaults(func=cmd_msgr_webhook)

    # Memory helpers
    mem = sub.add_parser("memory", help="Memory utilities")
    mem_sub = mem.add_subparsers(dest="mem_cmd", required=True)

    def _api_memory(contact: str, limit: int = 5):
        try:
            r = requests.get(f"{BASE_URL}/memory", params={"contact": contact, "limit": limit}, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status(); return r.json()
        except Exception as e:
            raise ClientError(f"/memory failed: {e}")

    def _api_memory_summary(contact: str, limit: int = 10):
        try:
            r = requests.get(f"{BASE_URL}/memory/summary", params={"contact": contact, "limit": limit}, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status(); return r.json()
        except Exception as e:
            raise ClientError(f"/memory/summary failed: {e}")

    def _api_memory_purge(contact: str):
        try:
            r = requests.delete(f"{BASE_URL}/memory", params={"contact": contact}, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status(); return r.json()
        except Exception as e:
            raise ClientError(f"DELETE /memory failed: {e}")

    def _cmd_mem_get(args: argparse.Namespace):
        pretty(_api_memory(args.contact, args.limit))
    def _cmd_mem_summary(args: argparse.Namespace):
        pretty(_api_memory_summary(args.contact, args.limit))
    def _cmd_mem_purge(args: argparse.Namespace):
        pretty(_api_memory_purge(args.contact))

    mg = mem_sub.add_parser("get", help="Get recent memory items")
    mg.add_argument("--contact", required=True)
    mg.add_argument("--limit", type=int, default=5)
    mg.set_defaults(func=_cmd_mem_get)

    msu = mem_sub.add_parser("summary", help="Summarize memory")
    msu.add_argument("--contact", required=True)
    msu.add_argument("--limit", type=int, default=10)
    msu.set_defaults(func=_cmd_mem_summary)

    mp = mem_sub.add_parser("purge", help="Purge memory for contact")
    mp.add_argument("--contact", required=True)
    mp.set_defaults(func=_cmd_mem_purge)

    # Transports registry
    tr = sub.add_parser("transports", help="Transport registry utilities")
    tr_sub = tr.add_subparsers(dest="tr_cmd", required=True)
    tr_list = tr_sub.add_parser("list", help="List available transports")
    def _cmd_tr_list(_: argparse.Namespace) -> None:
        pretty({"transports": sorted(TRANSPORT_REGISTRY.keys())})
    tr_list.set_defaults(func=_cmd_tr_list)

    tr_disc = tr_sub.add_parser("discover", help="Discover plugin transports under plugins/transports/")
    def _cmd_tr_discover(_: argparse.Namespace) -> None:
        pretty({"loaded": discover_transports()})
    tr_disc.set_defaults(func=_cmd_tr_discover)

    return p


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(verbose=bool(getattr(args, "verbose", False)))
    args.func(args)


if __name__ == "__main__":
    main()
