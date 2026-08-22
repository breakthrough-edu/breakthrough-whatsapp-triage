#!/usr/bin/env python3
"""Turn a full WhatsApp export into a small, mechanical digest.

One job: read the big JSON produced by the exporter, keep only the chats that
had real traffic inside a time window, and write a compact JSON file that a
reading session can hold in its head.

What this script must NEVER do:
  * judge anything. No priority, no urgency, no band, no "needs reply".
    Every number here is countable. The judgement happens later, in the
    session that reads this file.
  * invent a phone number. A group or an unresolvable contact gets
    reply_mode "copy" and no link. WhatsApp has no deep link that opens a
    group with prefilled text, so there is nothing to fake.
  * claim a message is unread. The export carries no unread signal at all
    (read_timestamp is always empty), so this file never pretends otherwise.
  * drop anything silently. Every skipped chat and every unparseable message
    is counted and reported.

Stdlib only. Python 3.9 and newer.
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCHEMA = "wa-digest/1"

EXIT_OK = 0
EXIT_EXPORT = 2
EXIT_CONFIG = 3

# Anything whose JID ends with one of these is a broadcast surface, not a chat.
BROADCAST_SUFFIXES = ("@broadcast", "@newsletter", "@lid.status", "@status")

DIGIT_RE = re.compile(r"\D")
# Same phone shape the board validator accepts, so a link written here can
# never fail validation later.
PHONE_RE = re.compile(r"^\d{6,15}$")

TRUE_STRINGS = {"true", "yes", "y", "t", "1"}
FALSE_STRINGS = {"false", "no", "n", "f", "0", "", "none", "null", "nil"}
# Only these exact spellings are treated as "no text". Lowercase "none" is
# left alone because a person can genuinely send the word none.
NULL_TEXT = {"None", "null", "NULL", "nil"}

MIN_EPOCH = 946684800     # 2000-01-01, anything older is treated as garbage
MAX_EPOCH = 4102444800    # 2100-01-01


# --------------------------------------------------------------------------
# coercers: the export is mostly well typed, but another platform or another
# exporter version can hand back a string where a bool was expected. These
# accept both and never raise.
# --------------------------------------------------------------------------

def as_bool(value, default=False):
    """Accept a real bool, a number, or the strings True / False / None."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        token = value.strip().lower()
        if token in TRUE_STRINGS:
            return True
        if token in FALSE_STRINGS:
            return False
    return default


def as_epoch(value):
    """Return whole unix seconds, or None when the value cannot be read.

    Timestamps in the export are a mix of int and float, so everything goes
    through float() first. Values that look like milliseconds or microseconds
    are scaled down, then anything outside a sane calendar range is rejected.
    """
    if value is None or isinstance(value, bool):
        return None
    number = None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        token = value.strip()
        if not token or token in NULL_TEXT:
            return None
        try:
            number = float(token)
        except ValueError:
            parsed = parse_when(token)
            number = parsed.timestamp() if parsed else None
    if number is None or number <= 0:
        return None
    for _ in range(3):
        if number <= MAX_EPOCH:
            break
        number = number / 1000.0
    if not (MIN_EPOCH <= number <= MAX_EPOCH):
        return None
    return int(number)


def as_text(value):
    """Return a string. Real None and the literal string None both mean empty."""
    if value is None:
        return ""
    if isinstance(value, str):
        return "" if value in NULL_TEXT else value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def parse_when(token):
    """Parse an ISO 8601 string (or a bare date) into an aware datetime."""
    if not isinstance(token, str):
        return None
    text = token.strip()
    if not text:
        return None
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.astimezone()
    return moment


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def local_iso(epoch):
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def local_short(epoch):
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")


def clip(text, limit):
    if text is None:
        return None
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def digits_of(token):
    return DIGIT_RE.sub("", token or "")


def classify_jid(jid):
    """One of: broadcast, group, direct_phone, direct_lid, direct_other."""
    low = (jid or "").lower()
    if low.endswith(BROADCAST_SUFFIXES):
        return "broadcast"
    if low.endswith("@g.us") or low.endswith("@groups.us"):
        return "group"
    if low.endswith("@s.whatsapp.net") or low.endswith("@c.us"):
        return "direct_phone"
    if low.endswith("@lid"):
        return "direct_lid"
    return "direct_other"


def jid_local_part(jid):
    """The part before the @, with any device suffix removed."""
    head = (jid or "").split("@", 1)[0]
    return head.split(":", 1)[0].split(".", 1)[0]


def fail(code, message, hint=""):
    """Print one line of JSON on stdout and stop. Callers parse this."""
    payload = {"ok": False, "error": message}
    if hint:
        payload["hint"] = hint
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.exit(code)


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------

CONFIG_KEYS = {
    "export_path": ("export_path", "export", "export_json"),
    "contacts_db": ("contacts_db", "contacts", "contacts_path", "contacts_db_path"),
    "work_dir": ("work_dir", "working_folder", "workdir"),
    "digest_path": ("digest_path", "out", "digest"),
    "link_style": ("link_style",),
    "days": ("days", "window_days"),
    "ignored_jids": ("ignored_jids", "ignore_jids"),
}

# Keys the skill writes that this script legitimately ignores.
KNOWN_EXTRA_KEYS = {
    "version", "setup_complete", "platform", "source",
    "default_window_days", "last_export_at", "last_export_max_ts",
    "last_run_at", "last_window_days", "smoke_ok_at",
}


def warn_unknown_keys(raw, warnings):
    """Say something when a config key was misspelled.

    A key this script does not recognise is silently ignored, and silence is
    the dangerous outcome: pointing `contacts_db` at the wrong key name costs
    every @lid reply button (12 of 37 on a real library) with no error and no
    visible difference except a quieter board.
    """
    known = set(KNOWN_EXTRA_KEYS)
    for aliases in CONFIG_KEYS.values():
        known.update(aliases)
    unknown = sorted(k for k in raw if k not in known)
    for key in unknown:
        warnings.append(
            "Config key %r is not recognised and was ignored. Check the "
            "spelling against setup docs, a wrong key fails quietly." % key)


def pick(raw, name):
    for alias in CONFIG_KEYS[name]:
        if alias in raw and raw[alias] not in (None, ""):
            return raw[alias]
    return None


def load_config(path_text):
    path = Path(path_text).expanduser()
    if not path.exists():
        fail(EXIT_CONFIG, "config file not found: %s" % path,
             "Run the setup step first, or pass the right path after --config.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        fail(EXIT_CONFIG, "config file is not valid JSON: %s" % err,
             "Open %s and check for a missing comma or quote." % path)
    if not isinstance(raw, dict):
        fail(EXIT_CONFIG, "config file must hold a JSON object",
             "The file should start with { and end with }.")

    base = path.parent

    def resolve(value):
        if value in (None, ""):
            return None
        candidate = Path(str(value)).expanduser()
        if not candidate.is_absolute():
            candidate = (base / candidate).resolve()
        return candidate

    cfg = {
        "config_path": path,
        "_raw": raw,
        "export_path": resolve(pick(raw, "export_path")),
        "contacts_db": resolve(pick(raw, "contacts_db")),
        "work_dir": resolve(pick(raw, "work_dir")),
        "digest_path": resolve(pick(raw, "digest_path")),
        "link_style": pick(raw, "link_style") or "app",
        "days": pick(raw, "days"),
        "ignored_jids": pick(raw, "ignored_jids") or [],
    }

    if cfg["link_style"] not in ("app", "web"):
        fail(EXIT_CONFIG, "link_style must be \"app\" or \"web\", found %r" % cfg["link_style"],
             "Use \"app\" for whatsapp://send links, \"web\" for wa.me links.")
    if cfg["days"] is not None:
        try:
            cfg["days"] = int(cfg["days"])
        except (TypeError, ValueError):
            fail(EXIT_CONFIG, "days must be a whole number, found %r" % cfg["days"])
        if cfg["days"] < 1:
            fail(EXIT_CONFIG, "days must be 1 or more, found %d" % cfg["days"])
    if not isinstance(cfg["ignored_jids"], list) or any(
            not isinstance(item, str) for item in cfg["ignored_jids"]):
        fail(EXIT_CONFIG, "ignored_jids must be a list of JID strings",
             "Example: \"ignored_jids\": [\"123456789@s.whatsapp.net\"]")
    return cfg


# --------------------------------------------------------------------------
# contacts join, for @lid chats
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# what counts as noise, and what counts as an unreadable gap
# --------------------------------------------------------------------------
#
# The exporter's `meta` flag does NOT mean "system message". It means "this
# body was generated by the tool rather than typed by a person". It is set for
# a missing media file, a deleted message, a group rename, a call record and a
# vCard summary. Measured on a real library, every single media message in the
# window carried meta true, so skipping on meta alone threw away 141 real
# messages and reported zero media gaps. A missing voice note is exactly the
# thing the board has to surface, so it must survive to be counted.
#
# Skip only bodies that carry no information about what anyone wants.

PLACEHOLDER_BODIES = {
    "the media is missing",
    "message deleted",
    "this message was deleted",
}

SYSTEM_BODY_PREFIXES = (
    "the group name changed to",
    "changed their phone number",
)


def is_placeholder_body(body):
    """True when `data` holds tool-generated filler, not user content."""
    return body.strip().lower() in PLACEHOLDER_BODIES


def is_system_noise(message):
    """True only for messages that tell us nothing about what anyone wants.

    Deliberately narrow. A media message is never noise, even when the file
    itself is missing, because an unreadable attachment is a fact the board
    must declare rather than hide.
    """
    if as_bool(message.get("media")):
        return False
    body = as_text(message.get("data")).strip().lower()
    if body in PLACEHOLDER_BODIES:
        return True
    if any(body.startswith(prefix) for prefix in SYSTEM_BODY_PREFIXES):
        return True
    # A meta message with no body at all carries nothing usable.
    return as_bool(message.get("meta")) and not body


def load_lid_map(db_path, warnings):
    """Map the local part of a @lid JID to a phone number.

    Soft failure by design: if the database is missing or locked the digest
    still gets built, every @lid chat is simply marked unresolved.
    """
    if db_path is None:
        warnings.append("No contacts database configured, so every @lid chat stays unresolved.")
        return {}
    path = Path(db_path).expanduser()
    if not path.exists():
        warnings.append("Contacts database not found at %s, every @lid chat stays unresolved." % path)
        return {}
    mapping = {}
    connection = None
    try:
        connection = sqlite3.connect("file:%s?mode=ro" % path.as_posix(), uri=True)
        cursor = connection.execute(
            "SELECT ZLID, ZPHONENUMBER FROM ZWAADDRESSBOOKCONTACT "
            "WHERE ZLID IS NOT NULL AND ZLID <> ''")
        for lid, phone in cursor.fetchall():
            key = jid_local_part(str(lid or ""))
            number = digits_of(str(phone or ""))
            if key and PHONE_RE.match(number):
                mapping.setdefault(key, number)
    except Exception as err:
        warnings.append("Could not read the contacts database (%s), every @lid chat stays "
                        "unresolved. The digest is still usable." % err)
        return {}
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    return mapping


# --------------------------------------------------------------------------
# the work
# --------------------------------------------------------------------------

def iter_messages(container):
    """Messages arrive as a dict keyed by message id. Lists are tolerated."""
    if isinstance(container, dict):
        for key in container:
            yield str(key), container[key]
    elif isinstance(container, list):
        for index, item in enumerate(container):
            yield str(index), item


def scan_chat(jid, chat, args, window):
    """Count and collect one chat. Returns (record, bad_samples)."""
    from_epoch, to_epoch = window
    bad_samples = []
    total = inbound = outbound = media_gaps = 0
    bad = 0
    last_epoch = last_in = last_out = None
    last_direction = None
    participants = set()
    rows = []

    for key, message in iter_messages(chat.get("messages")):
        if not isinstance(message, dict):
            bad += 1
            bad_samples.append({"jid": jid, "key": key, "raw": repr(message)[:400]})
            continue
        if is_system_noise(message):
            continue  # genuine protocol noise, never a human message
        stamp = as_epoch(message.get("timestamp"))
        if stamp is None:
            bad += 1
            bad_samples.append({"jid": jid, "key": key, "raw": message})
            continue
        if stamp < from_epoch or stamp > to_epoch:
            continue

        outgoing = as_bool(message.get("from_me"))
        body = as_text(message.get("data"))
        caption = as_text(message.get("caption"))
        has_media = as_bool(message.get("media"))
        if is_placeholder_body(body):
            body = ""  # tool-generated filler, not something the user wrote
        readable = body or caption

        total += 1
        if outgoing:
            outbound += 1
            if last_out is None or stamp > last_out:
                last_out = stamp
        else:
            inbound += 1
            if last_in is None or stamp > last_in:
                last_in = stamp
        if has_media and not readable:
            media_gaps += 1
        if last_epoch is None or stamp > last_epoch:
            last_epoch = stamp
            last_direction = "out" if outgoing else "in"

        sender = as_text(message.get("sender")).strip()
        if sender and not outgoing:
            participants.add(sender)

        mime = as_text(message.get("mime")).strip()
        media_label = None
        if has_media:
            if mime:
                media_label = mime
            elif message.get("message_type") is not None:
                media_label = "type:%s" % as_text(message.get("message_type"))
            else:
                media_label = "media"

        rows.append({
            "_ts": stamp,
            "_key": key,
            "dir": "out" if outgoing else "in",
            "sender": sender or None,
            "text": readable,
            "media": media_label,
            "quoted": as_text(message.get("quoted_data")).strip() or None,
        })

    if total == 0:
        return None, bad, bad_samples

    rows.sort(key=lambda row: (row["_ts"], row["_key"]))
    since_out = sum(1 for row in rows
                    if row["dir"] == "in" and (last_out is None or row["_ts"] > last_out))

    record = {
        "jid": jid,
        "name": as_text(chat.get("name")).strip(),
        "kind_raw": classify_jid(jid),
        "counts": {
            "total": total,
            "in": inbound,
            "out": outbound,
            "media_gaps": media_gaps,
        },
        "last_epoch": last_epoch,
        "last_direction": last_direction,
        "last_in": last_in,
        "last_out": last_out,
        "in_since_last_out": since_out,
        "participants": sorted(participants),
        "rows": rows[-max(1, args.max_transcript):],
    }
    return record, bad, bad_samples


def address_of(record, lid_map, link_style):
    """Work out phone, resolution, reply_mode and href_prefix for one chat."""
    kind_raw = record["kind_raw"]
    if kind_raw == "group":
        return None, "group", "copy", None

    phone = None
    resolution = "unresolved"
    if kind_raw == "direct_phone":
        candidate = digits_of(jid_local_part(record["jid"]))
        if PHONE_RE.match(candidate):
            phone = candidate
            resolution = "jid"
    elif kind_raw == "direct_lid":
        candidate = lid_map.get(jid_local_part(record["jid"]))
        if candidate and PHONE_RE.match(candidate):
            phone = candidate
            resolution = "contacts_join"

    if phone is None:
        return None, resolution, "copy", None
    if link_style == "web":
        prefix = "https://wa.me/%s?text=" % phone
    else:
        prefix = "whatsapp://send?phone=%s&text=" % phone
    return phone, resolution, "link", prefix


def render_chat(record, phone, resolution, reply_mode, href_prefix,
                transcript_cap, snippet_cap, now_epoch):
    kind = "group" if record["kind_raw"] == "group" else "direct"
    name = record["name"] or (phone or record["jid"])
    hours_ago = None
    if record["last_epoch"] is not None:
        hours_ago = round((now_epoch - record["last_epoch"]) / 3600.0, 1)

    transcript = []
    for row in record["rows"][-transcript_cap:] if transcript_cap else []:
        transcript.append({
            "t": local_short(row["_ts"]),
            "dir": row["dir"],
            "sender": row["sender"],
            "text": clip(row["text"], snippet_cap),
            "media": row["media"],
            "quoted": clip(row["quoted"], 80),
        })

    return {
        "jid": record["jid"],
        "kind": kind,
        "name": name,
        "phone": phone,
        "resolution": resolution,
        "reply_mode": reply_mode,
        "href_prefix": href_prefix,
        "counts": record["counts"],
        "last": {
            "at": local_iso(record["last_epoch"]),
            "direction": record["last_direction"],
            "hours_ago": hours_ago,
        },
        "last_in_at": local_iso(record["last_in"]),
        "last_out_at": local_iso(record["last_out"]),
        "in_since_last_out": record["in_since_last_out"],
        "participants_seen": record["participants"] if kind == "group" else [],
        "transcript": transcript,
    }


def encode(document):
    return json.dumps(document, ensure_ascii=False, indent=1, separators=(",", ":"))


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="wa_digest.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Shrink a full WhatsApp export into a small digest file.\n\n"
            "The export is one very large JSON holding every chat you have ever had.\n"
            "This script keeps the last few days of real conversation, counts what\n"
            "happened in each chat, and writes a much smaller JSON file. It makes no\n"
            "decisions about what matters: that comes later."),
        epilog=(
            "Typical run:\n"
            "  python3 wa_digest.py --config config.json\n\n"
            "Look at the last 3 days instead of the usual 7:\n"
            "  python3 wa_digest.py --config config.json --days 3\n\n"
            "Keep one chat you normally ignore:\n"
            "  python3 wa_digest.py --config config.json --include-jid 60123456789@s.whatsapp.net\n\n"
            "Exit codes: 0 finished (an empty window still counts as finished),\n"
            "2 the export file is missing or unreadable, 3 the config file is wrong.\n"
            "Failures print one line of JSON so a script can read them."))
    parser.add_argument("--config", required=True, metavar="PATH",
                        help="the config.json written during setup. Required.")
    parser.add_argument("--export", metavar="PATH",
                        help="the exported JSON, if it is not the one named in the config.")
    parser.add_argument("--contacts", metavar="PATH",
                        help="ContactsV2.sqlite, used to put phone numbers on hidden @lid chats. "
                             "Missing or unreadable is fine, those chats are marked unresolved.")
    parser.add_argument("--days", type=int, metavar="N",
                        help="how many days back to read. Default 7.")
    parser.add_argument("--now", metavar="ISO8601",
                        help="pretend the current time is this, for example 2026-08-23T09:00:00. "
                             "Used by the tests so a run can be repeated exactly.")
    parser.add_argument("--out", metavar="PATH",
                        help="where to write the digest. Default digest.json in the working folder.")
    parser.add_argument("--include-jid", action="append", default=[], metavar="JID",
                        help="always keep this chat, even when it is on the ignore list or had "
                             "no traffic. Repeatable.")
    parser.add_argument("--max-transcript", type=int, default=20, metavar="N",
                        help="how many recent messages to quote per chat. Default 20.")
    parser.add_argument("--max-snippet", type=int, default=240, metavar="N",
                        help="how many characters of each message to keep. Default 240.")
    parser.add_argument("--budget-bytes", type=int, default=150000, metavar="N",
                        help="size ceiling for the digest. Above this the script shortens "
                             "transcripts, then snippets, then drops the quietest chats, and "
                             "always says so. Default 150000.")
    parser.add_argument("--dump-bad", type=int, default=0, metavar="N",
                        help="write up to N unreadable raw messages to a side file, so you can "
                             "paste them when asking for help. Default 0, which writes nothing.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.max_transcript < 0 or args.max_snippet < 0 or args.budget_bytes < 1:
        fail(EXIT_CONFIG, "max-transcript, max-snippet and budget-bytes must be positive numbers")

    cfg = load_config(args.config)
    warnings = []
    warn_unknown_keys(cfg.get("_raw", {}), warnings)

    days = args.days if args.days is not None else (cfg["days"] or 7)
    if days < 1:
        fail(EXIT_CONFIG, "days must be 1 or more, found %d" % days)

    now_dt = parse_when(args.now) if args.now else datetime.now().astimezone()
    if args.now and now_dt is None:
        fail(EXIT_CONFIG, "could not read --now %r" % args.now,
             "Use something like 2026-08-23T09:00:00.")
    now_epoch = int(now_dt.timestamp())
    from_epoch = now_epoch - days * 86400

    export_path = Path(args.export).expanduser() if args.export else cfg["export_path"]
    if export_path is None:
        fail(EXIT_EXPORT, "no export file named in the config and none given with --export",
             "Run the export step first, then point the config at the JSON it produced.")
    export_path = Path(export_path)
    if not export_path.exists():
        fail(EXIT_EXPORT, "export file not found: %s" % export_path,
             "Check the path in your config, or run the export step again.")
    try:
        export = json.loads(export_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as err:
        fail(EXIT_EXPORT, "export file could not be read as JSON: %s" % err,
             "The export may be half written. Run the export again and wait for it to finish.")
    if not isinstance(export, dict):
        fail(EXIT_EXPORT, "export file does not look like a WhatsApp export",
             "The top level should be an object of chats keyed by JID.")

    contacts_path = Path(args.contacts).expanduser() if args.contacts else cfg["contacts_db"]
    lid_map = load_lid_map(contacts_path, warnings)

    ignored = set(cfg["ignored_jids"])
    forced = set(args.include_jid or [])

    pruned = {"empty_window": 0, "broadcast": 0, "ignored": 0}
    export_min = export_max = None
    export_messages = 0
    bad_total = 0
    bad_samples = []
    records = []

    for jid in sorted(export.keys()):
        chat = export[jid]
        if not isinstance(chat, dict):
            continue
        container = chat.get("messages")
        if isinstance(container, dict):
            export_messages += len(container)
        elif isinstance(container, list):
            export_messages += len(container)

        forced_in = jid in forced
        kind_raw = classify_jid(jid)
        if not forced_in:
            if kind_raw == "broadcast":
                pruned["broadcast"] += 1
                continue
            if jid in ignored:
                pruned["ignored"] += 1
                continue

        record, bad, samples = scan_chat(jid, chat, args, (from_epoch, now_epoch))
        bad_total += bad
        if samples and len(bad_samples) < 500:
            bad_samples.extend(samples[:500 - len(bad_samples)])

        if record is None:
            if forced_in:
                # A forced chat with nothing in the window still shows up, so the
                # reader can see the silence rather than wonder where it went.
                record = {
                    "jid": jid, "name": as_text(chat.get("name")).strip(),
                    "kind_raw": kind_raw,
                    "counts": {"total": 0, "in": 0, "out": 0, "media_gaps": 0},
                    "last_epoch": None, "last_direction": None,
                    "last_in": None, "last_out": None,
                    "in_since_last_out": 0, "participants": [], "rows": [],
                }
            else:
                pruned["empty_window"] += 1
                continue
        records.append(record)

    # Export freshness, measured across every message the file holds.
    for jid in export:
        chat = export[jid]
        if not isinstance(chat, dict):
            continue
        for _key, message in iter_messages(chat.get("messages")):
            if not isinstance(message, dict):
                continue
            stamp = as_epoch(message.get("timestamp"))
            if stamp is None:
                continue
            if export_min is None or stamp < export_min:
                export_min = stamp
            if export_max is None or stamp > export_max:
                export_max = stamp

    records.sort(key=lambda item: (-(item["last_epoch"] or 0), item["jid"]))

    addressed = []
    for record in records:
        phone, resolution, reply_mode, prefix = address_of(record, lid_map, cfg["link_style"])
        addressed.append((record, phone, resolution, reply_mode, prefix))

    groups = sum(1 for item in addressed if item[0]["kind_raw"] == "group")
    directs = len(addressed) - groups
    linkable = sum(1 for item in addressed if item[3] == "link")
    lid_unresolved = sum(1 for item in addressed
                         if item[0]["kind_raw"] == "direct_lid" and item[2] == "unresolved")
    messages = sum(item[0]["counts"]["total"] for item in addressed)
    inbound = sum(item[0]["counts"]["in"] for item in addressed)
    outbound = sum(item[0]["counts"]["out"] for item in addressed)
    media_gaps = sum(item[0]["counts"]["media_gaps"] for item in addressed)

    if bad_total:
        warnings.append("%d message(s) had no readable timestamp and were skipped. "
                        "Rerun with --dump-bad 20 to see them." % bad_total)
    if not addressed:
        warnings.append("No chat had traffic in the last %d day(s). Try a longer window "
                        "with --days, or export again if the export looks old." % days)
    if export_max is not None:
        age_hours = round((now_epoch - export_max) / 3600.0, 1)
        if age_hours > 48:
            warnings.append("The newest message in the export is %.1f hours old, so this "
                            "digest cannot see anything more recent." % age_hours)
    else:
        age_hours = None

    header = {
        "schema": SCHEMA,
        "generated_at": local_iso(now_epoch),
        "window": {
            "days": days,
            "from": local_iso(from_epoch),
            "to": local_iso(now_epoch),
            "from_epoch": from_epoch,
            "to_epoch": now_epoch,
        },
        "export": {
            "path": str(export_path),
            "max_ts": local_iso(export_max),
            "min_ts": local_iso(export_min),
            "age_hours": age_hours,
            "total_chats": len(export),
            "total_messages": export_messages,
        },
    }

    # Fixed degrade ladder. Never widens beyond what the caller asked for.
    ladder = []
    for transcript_cap, snippet_cap in ((args.max_transcript, args.max_snippet),
                                        (10, args.max_snippet),
                                        (10, 120),
                                        (5, 120)):
        step = (min(transcript_cap, args.max_transcript), min(snippet_cap, args.max_snippet))
        if step not in ladder:
            ladder.append(step)

    def build(step, kept_count):
        """Assemble one candidate. Its own warnings are inside it before it is
        measured, so what gets weighed is exactly what gets written."""
        notes = list(warnings)
        if step != (args.max_transcript, args.max_snippet):
            notes.append(
                "Digest was over the %d byte budget, so transcripts were cut to %d message(s) "
                "and snippets to %d character(s)." % (args.budget_bytes, step[0], step[1]))
        dropped = len(addressed) - kept_count
        if dropped > 0:
            notes.append(
                "%d chat(s) were left out of this file to stay under the size budget. They are "
                "the quietest ones by last activity, and they are still counted in the summary."
                % dropped)
        candidate = assemble(header, addressed, groups, directs, linkable, lid_unresolved,
                             messages, inbound, outbound, media_gaps, pruned, dropped,
                             notes, step, now_epoch, kept_count)
        return candidate, encode(candidate)

    def fits(text):
        # The file gets one trailing newline, so it counts toward the budget.
        return len(text.encode("utf-8")) + 1 <= args.budget_bytes

    used = ladder[0]
    kept = len(addressed)
    document, payload = build(used, kept)
    for step in ladder[1:]:
        if fits(payload):
            break
        used = step
        document, payload = build(used, kept)

    if not fits(payload) and addressed:
        # Still too big at the tightest setting: keep the most recently active
        # chats and say exactly how many were left out.
        low, high = 1, len(addressed)
        best = None
        while low <= high:
            middle = (low + high) // 2
            trial, encoded = build(used, middle)
            if fits(encoded):
                best = (trial, encoded, middle)
                low = middle + 1
            else:
                high = middle - 1
        if best is None:
            trial, encoded = build(used, 1)
            best = (trial, encoded, 1)
        document, payload, kept = best

    if args.out:
        out_path = Path(args.out).expanduser()
    elif cfg["digest_path"]:
        out_path = cfg["digest_path"]
    elif cfg["work_dir"]:
        out_path = cfg["work_dir"] / "digest.json"
    else:
        out_path = Path.cwd() / "digest.json"
    out_path = Path(out_path)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload + "\n", encoding="utf-8")
    except Exception as err:
        fail(EXIT_EXPORT, "could not write the digest to %s: %s" % (out_path, err),
             "Pick a folder you can write to with --out.")

    bad_path = None
    if args.dump_bad > 0 and bad_samples:
        bad_path = out_path.with_name(out_path.stem + ".bad.json")
        try:
            bad_path.write_text(
                json.dumps(bad_samples[:args.dump_bad], ensure_ascii=False, indent=1,
                           default=repr) + "\n", encoding="utf-8")
        except Exception as err:
            document["warnings"].append("Could not write the sample file: %s" % err)
            bad_path = None

    sys.stdout.write(json.dumps({
        "ok": True,
        "out": str(out_path),
        "bytes": len(payload.encode("utf-8")) + 1,
        "chats": len(document["chats"]),
        "messages": messages,
        "window_days": days,
        "warnings": len(document["warnings"]),
        "bad_messages": bad_total,
        "bad_sample_file": str(bad_path) if bad_path else None,
    }, ensure_ascii=False) + "\n")
    return EXIT_OK


def assemble(header, addressed, groups, directs, linkable, lid_unresolved, messages,
             inbound, outbound, media_gaps, pruned, truncated, warnings, step,
             now_epoch, kept):
    transcript_cap, snippet_cap = step
    document = dict(header)
    document["summary"] = {
        "active_chats": groups + directs,
        "groups": groups,
        "directs": directs,
        "linkable_directs": linkable,
        "lid_unresolved": lid_unresolved,
        "messages": messages,
        "inbound": inbound,
        "outbound": outbound,
        "media_gaps": media_gaps,
        "pruned": dict(pruned),
        "truncated_chats": truncated,
    }
    document["warnings"] = warnings
    document["chats"] = [
        render_chat(record, phone, resolution, reply_mode, prefix,
                    transcript_cap, snippet_cap, now_epoch)
        for record, phone, resolution, reply_mode, prefix in addressed[:kept]
    ]
    return document


if __name__ == "__main__":
    sys.exit(main())
