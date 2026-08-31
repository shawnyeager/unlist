#!/usr/bin/env python3
"""Unlist — local data-broker removal agent.

No network calls. Generates scan queries, work queues, and request letters
from profile.json + data/brokers.json. You (or a Grok Bot) execute the
forms and emails. State stays on disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROFILE_PATH = ROOT / "profile.json"
EXAMPLE_PATH = ROOT / "profile.example.json"
BROKERS_PATH = DATA / "brokers.json"
STATE_PATH = DATA / "state.json"
LETTER_TMPL = ROOT / "templates" / "deletion-request.md"
AUTH_TMPL = ROOT / "templates" / "authorization.md"
LOG_PATH = ROOT / "logs" / "actions.jsonl"


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def load_profile() -> dict:
    data = load_json(PROFILE_PATH)
    if not data:
        sys.exit(f"Missing {PROFILE_PATH}. Run: python scripts/unlist.py init")
    return data


def load_brokers() -> list[dict]:
    raw = load_json(BROKERS_PATH)
    if not raw:
        sys.exit(f"Missing {BROKERS_PATH}")
    return raw["brokers"]


def load_state() -> dict:
    return load_json(STATE_PATH) or {"requests": {}, "custom": []}


def save_state(state: dict) -> None:
    save_json(STATE_PATH, state)


def broker_by_id(brokers: list[dict], ident: str) -> dict:
    ident = ident.lower()
    for b in brokers:
        if b["id"] == ident or b["name"].lower() == ident:
            return b
    sys.exit(f"Unknown broker: {ident}. Try: python scripts/unlist.py queue")


def fmt_addresses(profile: dict) -> str:
    lines = []
    for a in profile.get("addresses") or []:
        bit = f"{a.get('line1', '')}, {a.get('city', '')}, {a.get('state', '')} {a.get('postal_code', '')}".strip()
        if a.get("current"):
            bit += " (current)"
        lines.append(bit)
    return "; ".join(lines) or "(none provided)"


def law_line(profile: dict) -> str:
    state = (profile.get("state_of_residence") or "").upper()
    if profile.get("california_resident") or state == "CA":
        return "I am a California resident. Process this under the CCPA/CPRA."
    rights = {
        "VA": "Virginia CDPA",
        "CO": "Colorado CPA",
        "CT": "Connecticut CTDPA",
        "UT": "Utah UCPA",
        "TX": "Texas TDPSA",
        "OR": "Oregon OCPA",
        "MT": "Montana MCDPA",
        "TN": "Tennessee TIPA",
        "DE": "Delaware PDPA",
        "NJ": "New Jersey NJSDA",
        "NH": "New Hampshire",
        "IA": "Iowa ICDPA",
        "IN": "Indiana",
        "KY": "Kentucky",
        "MD": "Maryland",
        "MN": "Minnesota",
        "NE": "Nebraska",
    }
    if state in rights:
        return f"I reside in {state}. Process this under {rights[state]} and any other law that applies."
    return "Process this under any U.S. state privacy law that applies to you, and honor the request even if you believe no statute compels it."


def fill_template(text: str, mapping: dict) -> str:
    out = text
    for k, v in mapping.items():
        out = out.replace("{{ " + k + "}}", v) if False else out.replace("{{" + k + "}}", v)
    return out


def cmd_init(_args) -> None:
    if not PROFILE_PATH.exists():
        PROFILE_PATH.write_text(EXAMPLE_PATH.read_text())
        print(f"Wrote {PROFILE_PATH} from example. Edit it with your real identifiers.")
    else:
        print(f"{PROFILE_PATH} already exists.")
    state = load_state()
    save_state(state)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    print("Next: edit profile.json, then run `python scripts/unlist.py queries` and `queue`.")


def cmd_queries(_args) -> None:
    p = load_profile()
    names = [p["legal_name"], *(p.get("aliases") or [])]
    cities = sorted({a.get("city") for a in p.get("addresses") or [] if a.get("city")})
    brokers = [b for b in load_brokers() if b.get("search_url")]
    print("# Search queries — run these, copy listing URLs, then log them\n")
    for name in names:
        for city in cities or [""]:
            loc = f' "{city}"' if city else ""
            print(f'"{name}"{loc}')
            print(f'"{name}"{loc} (spokeo OR whitepages OR beenverified OR radaris OR mylife)')
        for phone in p.get("phones") or []:
            print(f'"{phone}"')
        for email in p.get("emails") or []:
            print(f'"{email}"')
    print("\n# Site-restricted")
    for b in brokers:
        host = (b.get("search_url") or "").replace("https://", "").replace("http://", "").split("/")[0]
        if not host:
            continue
        print(f'site:{host} "{p["legal_name"]}"')


def cmd_queue(args) -> None:
    brokers = load_brokers()
    state = load_state()
    wave = args.wave
    rows = []
    for b in brokers:
        if wave is not None and b.get("wave") != wave:
            continue
        rec = state["requests"].get(b["id"], {})
        status = rec.get("status", "pending")
        if args.open and status in {"completed", "skipped"}:
            continue
        rows.append((b.get("priority", 0), b.get("wave", 9), b, status, rec))
    rows.sort(key=lambda r: (-r[0], r[1], r[2]["id"]))
    print(f"{'id':<22} {'wave':<5} {'pri':<4} {'status':<16} {'opt-out'}")
    print("-" * 100)
    for _, _, b, status, rec in rows:
        url = b.get("opt_out_url") or b.get("email") or ""
        extra = f"  last={rec['updated'][:10]}" if rec.get("updated") else ""
        print(f"{b['id']:<22} {b.get('wave', '-'):<5} {b.get('priority', 0):<4} {status:<16} {url}{extra}")
    print(f"\n{len(rows)} brokers. Use: python scripts/unlist.py show ID | letter ID | next")


def cmd_show(args) -> None:
    b = broker_by_id(load_brokers(), args.broker)
    rec = load_state()["requests"].get(b["id"], {})
    print(json.dumps({**b, "record": rec}, indent=2))


def mapping_for(profile: dict, broker: dict | None, listing_url: str = "") -> dict:
    aliases = ", ".join(profile.get("aliases") or []) or "(none)"
    dob = profile.get("date_of_birth")
    return {
        "legal_name": profile["legal_name"],
        "aliases": aliases,
        "emails": ", ".join(profile.get("emails") or []) or "(none)",
        "phones": ", ".join(profile.get("phones") or []) or "(none)",
        "addresses": fmt_addresses(profile),
        "dob_line": f"- Date of birth: {dob}" if dob else "",
        "broker_name": broker["name"] if broker else "the site at the URL below",
        "listing_url": listing_url or "(not yet found — search your name and attach the profile URL if you have it)",
        "law_line": law_line(profile),
        "agent_name": profile.get("agent_name") or "[your name / this agent]",
        "date": date.today().isoformat(),
    }


def cmd_letter(args) -> None:
    profile = load_profile()
    broker = broker_by_id(load_brokers(), args.broker)
    text = fill_template(LETTER_TMPL.read_text(), mapping_for(profile, broker, args.url or ""))
    print(text)
    if broker.get("opt_out_url"):
        print(f"\n---\nOpt-out URL: {broker['opt_out_url']}")
    if broker.get("email"):
        print(f"Email: {broker['email']}")
    if broker.get("steps"):
        print("Steps:")
        for i, s in enumerate(broker["steps"], 1):
            print(f"  {i}. {s}")


def cmd_auth(_args) -> None:
    profile = load_profile()
    print(fill_template(AUTH_TMPL.read_text(), mapping_for(profile, None)))


def cmd_custom(args) -> None:
    profile = load_profile()
    fake = {"name": args.url}
    print(fill_template(LETTER_TMPL.read_text(), mapping_for(profile, fake, args.url)))
    print("\n---\nAgent notes")
    print("1. Open the URL. Confirm it is actually this person.")
    print("2. Find Privacy / Do Not Sell / CCPA / Remove my info.")
    print("3. If a form exists, use the form and keep this letter as backup.")
    print("4. If only an email exists, send this letter.")
    print("5. Log it: python scripts/unlist.py log-custom URL sent")


def append_log(event: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(event) + "\n")


def cmd_log(args) -> None:
    brokers = load_brokers()
    broker = broker_by_id(brokers, args.broker)
    state = load_state()
    rec = state["requests"].get(broker["id"], {})
    rec.update(
        {
            "status": args.status,
            "updated": datetime.now(timezone.utc).isoformat(),
            "note": args.note or rec.get("note"),
            "listing_url": args.url or rec.get("listing_url"),
        }
    )
    if args.status == "sent":
        rec["sent_at"] = rec["updated"]
        rec["follow_up_on"] = (date.today() + timedelta(days=broker.get("sla_days") or 14)).isoformat()
    if args.status == "completed":
        rec["completed_at"] = rec["updated"]
        rec["recheck_on"] = (date.today() + timedelta(days=broker.get("recur_days") or 90)).isoformat()
    state["requests"][broker["id"]] = rec
    save_state(state)
    append_log({"ts": rec["updated"], "broker": broker["id"], "status": args.status, "note": args.note, "url": args.url})
    print(json.dumps(rec, indent=2))


def cmd_log_custom(args) -> None:
    state = load_state()
    entry = {
        "url": args.url,
        "status": args.status,
        "updated": datetime.now(timezone.utc).isoformat(),
        "note": args.note,
    }
    state["custom"].append(entry)
    save_state(state)
    append_log({"ts": entry["updated"], "broker": "custom", **entry})
    print(json.dumps(entry, indent=2))


def cmd_status(_args) -> None:
    state = load_state()
    brokers = {b["id"]: b for b in load_brokers()}
    counts: dict[str, int] = {}
    follow = []
    recheck = []
    for bid, rec in state["requests"].items():
        st = rec.get("status", "pending")
        counts[st] = counts.get(st, 0) + 1
        if rec.get("follow_up_on") and st in {"sent", "waiting_verify"}:
            follow.append((rec["follow_up_on"], bid, rec))
        if rec.get("recheck_on") and st == "completed":
            recheck.append((rec["recheck_on"], bid, rec))
    print("Counts:", json.dumps(counts or {"pending": len(brokers)}, indent=2))
    print(f"Custom URLs logged: {len(state.get('custom') or [])}")
    today = date.today().isoformat()
    due_f = [x for x in follow if x[0] <= today]
    due_r = [x for x in recheck if x[0] <= today]
    if due_f:
        print("\nFollow-ups due:")
        for when, bid, rec in sorted(due_f):
            print(f"  {when}  {bid}  {brokers.get(bid, {}).get('opt_out_url', '')}")
    if due_r:
        print("\nRechecks due (likely re-listed):")
        for when, bid, rec in sorted(due_r):
            print(f"  {when}  {bid}")
    if not due_f and not due_r:
        print("\nNo follow-ups or rechecks due today.")


def in_scope(broker: dict, profile: dict) -> bool:
    if broker.get("id") == "ca-drop":
        return bool(profile.get("california_resident") or (profile.get("state_of_residence") or "").upper() == "CA")
    return True


def cmd_next(_args) -> None:
    state = load_state()
    profile = load_profile()
    open_status = {"pending", "found"}
    ranked = sorted(load_brokers(), key=lambda b: (-b.get("priority", 0), b.get("wave", 9)))
    for b in ranked:
        if not in_scope(b, profile):
            continue
        st = state["requests"].get(b["id"], {}).get("status", "pending")
        if st in open_status:
            print(f"NEXT {b['id']}  ({b['name']})  wave {b.get('wave')}  {st}")
            print(f"opt-out: {b.get('opt_out_url') or b.get('email')}")
            if b.get("steps"):
                for i, s in enumerate(b["steps"], 1):
                    print(f"  {i}. {s}")
            print(f"\nLetter:\n  python scripts/unlist.py letter {b['id']}")
            print(f"After you submit:\n  python scripts/unlist.py log {b['id']} sent")
            return
    print("Queue clear. Run status for follow-ups, or log a custom URL.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="unlist", description="Local data-broker removal agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("queries").set_defaults(func=cmd_queries)
    q = sub.add_parser("queue")
    q.add_argument("--wave", type=int)
    q.add_argument("--open", action="store_true", help="hide completed/skipped")
    q.set_defaults(func=cmd_queue)
    s = sub.add_parser("show")
    s.add_argument("broker")
    s.set_defaults(func=cmd_show)
    l = sub.add_parser("letter")
    l.add_argument("broker")
    l.add_argument("--url", default="")
    l.set_defaults(func=cmd_letter)
    sub.add_parser("auth").set_defaults(func=cmd_auth)
    c = sub.add_parser("custom")
    c.add_argument("url")
    c.set_defaults(func=cmd_custom)
    lg = sub.add_parser("log")
    lg.add_argument("broker")
    lg.add_argument(
        "status",
        choices=["pending", "found", "sent", "waiting_verify", "completed", "failed", "skipped", "reappeared"],
    )
    lg.add_argument("--note")
    lg.add_argument("--url")
    lg.set_defaults(func=cmd_log)
    lc = sub.add_parser("log-custom")
    lc.add_argument("url")
    lc.add_argument("status")
    lc.add_argument("--note")
    lc.set_defaults(func=cmd_log_custom)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("next").set_defaults(func=cmd_next)
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
