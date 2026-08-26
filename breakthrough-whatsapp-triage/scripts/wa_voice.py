#!/usr/bin/env python3
"""wa_voice.py - sample the user's OWN sent messages into a voice corpus.

Why this script exists: the tone-of-voice profile is drafted from how the
user actually writes, and the only honest corpus is their own outgoing
messages in the export. Rule 1 of the skill says the raw export never
enters the model's context, so this script does the opening and hands back
a small sampled corpus file instead.

Division of labour (rule 9): this script computes facts, samples and
counts. It decides nothing about tone. The session reads the corpus file,
drafts tov-profile.md from it, and the user rules on the draft.

Privacy bar, same as wa_doctor.py: stdout carries counts, sizes and dates
only, never message content. The content goes into the --out file, which
lives in the working folder like everything else.

Exit codes: 0 ok · 3 config problem · 4 export problem (mirrors wa_digest).
"""

import argparse
import json
import sys
import time
from pathlib import Path

EXIT_OK = 0
EXIT_CONFIG = 3
EXIT_EXPORT = 4

# Keep the whole corpus small: it rides into a model context.
DEFAULT_PER_BUCKET = 60
DEFAULT_MAX_CHARS = 280
DEFAULT_BUDGET_BYTES = 80_000

CONFIG_ALIASES = {
    "export_path": ("export_path", "export", "export_json"),
    "work_dir": ("work_dir", "workdir", "working_folder"),
    "ignored_jids": ("ignored_jids", "ignore_jids"),
}

# Bodies the export tool writes for unreadable media; not the user's words.
PLACEHOLDER_BODIES = {"", "<media omitted>", "null", "none"}


def fail(code, message, hint=""):
    print("wa_voice: %s" % message, file=sys.stderr)
    if hint:
        print("  %s" % hint, file=sys.stderr)
    sys.exit(code)


def pick(raw, canonical):
    for key in CONFIG_ALIASES.get(canonical, (canonical,)):
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None


def load_config(path_text):
    path = Path(path_text).expanduser()
    if not path.exists():
        fail(EXIT_CONFIG, "config file not found: %s" % path,
             "Run setup first, or pass the right path after --config.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        fail(EXIT_CONFIG, "config file is not valid JSON: %s" % err)
    if not isinstance(raw, dict):
        fail(EXIT_CONFIG, "config file must hold a JSON object")
    base = path.parent

    def resolve(value):
        if value in (None, ""):
            return None
        candidate = Path(str(value)).expanduser()
        if not candidate.is_absolute():
            candidate = (base / candidate).resolve()
        return candidate

    ignored = pick(raw, "ignored_jids") or []
    if not isinstance(ignored, list):
        ignored = []
    return {
        "export_path": resolve(pick(raw, "export_path")),
        "work_dir": resolve(pick(raw, "work_dir")) or base,
        "ignored_jids": {str(j).strip().lower() for j in ignored if str(j).strip()},
    }


def is_group(jid):
    low = str(jid).lower()
    return low.endswith("@g.us") or low.endswith("@groups.us")


def as_epoch(value):
    try:
        stamp = float(value)
    except (TypeError, ValueError):
        return None
    if stamp > 1e12:  # milliseconds
        stamp /= 1000.0
    if stamp <= 0:
        return None
    return stamp


def iter_messages(container):
    if isinstance(container, dict):
        for key in container:
            yield container[key]
    elif isinstance(container, list):
        for item in container:
            yield item


def readable_body(message):
    """The user's own words, or None. Captions count: they wrote those too."""
    for field in ("data", "caption"):
        value = message.get(field)
        if isinstance(value, str):
            text = value.strip()
            if text and text.lower() not in PLACEHOLDER_BODIES:
                return text
    return None


def collect(export, ignored):
    """Walk every chat, keep the user's outgoing readable messages."""
    buckets = {"direct": [], "group": []}
    chats_scanned = 0
    out_total = 0
    if not isinstance(export, dict):
        fail(EXIT_EXPORT, "export root is not a JSON object")
    for jid, chat in export.items():
        if not isinstance(chat, dict):
            continue
        if str(jid).strip().lower() in ignored:
            continue
        chats_scanned += 1
        kind = "group" if is_group(jid) else "direct"
        for message in iter_messages(chat.get("messages")):
            if not isinstance(message, dict):
                continue
            if not message.get("from_me"):
                continue
            stamp = as_epoch(message.get("timestamp"))
            text = readable_body(message)
            if stamp is None or text is None:
                continue
            out_total += 1
            buckets[kind].append((stamp, jid, text))
    return buckets, chats_scanned, out_total


def sample(bucket, per_bucket, max_chars):
    """Newest first, at most two per chat, so one chatty thread cannot own
    the corpus and the sample spans many counterparts."""
    bucket.sort(key=lambda row: row[0], reverse=True)
    taken = []
    per_chat = {}
    for stamp, jid, text in bucket:
        if per_chat.get(jid, 0) >= 2:
            continue
        per_chat[jid] = per_chat.get(jid, 0) + 1
        taken.append({
            "ts": time.strftime("%Y-%m-%d", time.localtime(stamp)),
            "chars": len(text),
            "text": text[:max_chars],
        })
        if len(taken) >= per_bucket:
            break
    return taken


def length_stats(bucket):
    lengths = sorted(len(text) for _stamp, _jid, text in bucket)
    if not lengths:
        return None
    def pct(p):
        return lengths[min(len(lengths) - 1, int(len(lengths) * p))]
    return {"count": len(lengths), "p50_chars": pct(0.5), "p90_chars": pct(0.9)}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Sample the user's own sent messages into a small voice corpus.")
    parser.add_argument("--config", required=True, metavar="PATH")
    parser.add_argument("--export", metavar="PATH",
                        help="override the export path in the config")
    parser.add_argument("--out", metavar="PATH",
                        help="corpus file (default: <work_dir>/voice-corpus.json)")
    parser.add_argument("--per-bucket", type=int, default=DEFAULT_PER_BUCKET)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    export_path = Path(args.export).expanduser() if args.export else cfg["export_path"]
    if export_path is None:
        fail(EXIT_CONFIG, "no export path in config and none passed with --export")
    if not export_path.exists():
        fail(EXIT_EXPORT, "export file not found: %s" % export_path)
    try:
        export = json.loads(Path(export_path).read_text(encoding="utf-8"))
    except Exception as err:
        fail(EXIT_EXPORT, "export is not readable JSON: %s" % err)

    buckets, chats_scanned, out_total = collect(export, cfg["ignored_jids"])

    corpus = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M"),
        "export_file": str(export_path),
        "stats": {
            "chats_scanned": chats_scanned,
            "outgoing_readable_total": out_total,
            "direct": length_stats(buckets["direct"]),
            "group": length_stats(buckets["group"]),
        },
        "samples": {
            "direct": sample(buckets["direct"], args.per_bucket, args.max_chars),
            "group": sample(buckets["group"], args.per_bucket, args.max_chars),
        },
    }

    payload = json.dumps(corpus, ensure_ascii=False, indent=1)
    # Stay inside the byte budget: halve the sample until it fits.
    per = args.per_bucket
    while len(payload.encode("utf-8")) > DEFAULT_BUDGET_BYTES and per > 5:
        per //= 2
        corpus["samples"] = {
            "direct": sample(buckets["direct"], per, args.max_chars),
            "group": sample(buckets["group"], per, args.max_chars),
        }
        payload = json.dumps(corpus, ensure_ascii=False, indent=1)

    out_path = Path(args.out).expanduser() if args.out else cfg["work_dir"] / "voice-corpus.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(payload, encoding="utf-8")

    # Counts only on stdout, never content: same bar as wa_doctor.
    print("wa_voice: scanned %d chats, found %d outgoing readable messages, "
          "sampled %d direct + %d group into %s (%d bytes)" % (
              chats_scanned, out_total,
              len(corpus["samples"]["direct"]), len(corpus["samples"]["group"]),
              out_path, len(payload.encode("utf-8"))))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
