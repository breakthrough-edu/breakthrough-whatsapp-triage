#!/usr/bin/env python3
"""Print one paste-ready report about why the WhatsApp export is not working.

One job: look at every layer between a bare computer and a finished export
(operating system, Python, pip, the exporter package, the config file, the
phone backup, the database, the export JSON), and say which layer is the
first one that is broken.

What this script must NEVER do:
  * print message text, contact names, phone numbers, or a backup password
    or encryption key. Counts, file sizes and dates only. The whole point is
    that the report can be pasted into a chat window safely.
  * stop halfway. Every section catches its own errors and prints them as one
    line, because half a report is worse than no report.
  * change anything. It only reads.

Standard library only, on purpose: this has to run when pip itself is broken
and when there is no virtual environment.
"""

import argparse
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

APPLE_EPOCH = 978307200  # Core Data counts seconds from 2001-01-01

FULL_DISK_ACCESS_REMEDY = """  macOS blocked this folder. Grant Full Disk Access, then run this again:
    1. Open System Settings, then Privacy and Security, then Full Disk Access.
    2. Switch on the app you are running this from (Terminal, iTerm, or your editor).
    3. Quit that app completely (Command Q) and open it again. A restart of the
       app is required, the switch alone does not take effect.
    4. Run this doctor again."""

PREFERRED_INVOCATION = "python3 -m Whatsapp_Chat_Exporter"

INTERESTING_NAMES = (
    "msgstore.db.crypt15",
    "msgstore.db.crypt14",
    "msgstore.db",
    "ChatStorage.sqlite",
    "ContactsV2.sqlite",
    "wa.db",
    "export.json",
    "result.json",
)

CONFIG_NAMES = ("config.json", "wa-triage-config.json", "whatsapp-triage.json")

SECRET_HINTS = ("key", "password", "passphrase", "secret", "token", "pin")

_state = {"failures": []}


# --------------------------------------------------------------------------
# printing helpers
# --------------------------------------------------------------------------

def tilde(path):
    """Show a path without exposing the account name."""
    try:
        text = str(path)
        home = str(Path.home())
        if text.startswith(home):
            return "~" + text[len(home):]
        return text
    except Exception:
        return str(path)


def say(line=""):
    sys.stdout.write(line + "\n")


def head(name):
    say()
    say("[%s]" % name)


def note_failure(layer):
    if layer not in _state["failures"]:
        _state["failures"].append(layer)


def run_section(layer, title, function, *args):
    """Run one section. An exception here prints one line and the report goes on."""
    head(title)
    try:
        function(*args)
    except Exception as err:
        say("  section failed: %s: %s" % (type(err).__name__, err))
        say("  (the rest of the report still follows)")
        if os.environ.get("WA_DOCTOR_TRACE"):
            for line in traceback.format_exc().splitlines():
                say("  | " + line)
        note_failure(layer)


def stat_line(path):
    """EXISTS / not found / PERMISSION DENIED, with size and date."""
    path = Path(path)
    try:
        info = path.stat()
    except FileNotFoundError:
        return "not found"
    except PermissionError:
        return "PERMISSION DENIED"
    except OSError as err:
        return "unreadable (%s)" % err.strerror
    when = datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M")
    if path.is_dir():
        try:
            count = sum(1 for _ in path.iterdir())
            return "EXISTS  folder, %d item(s), changed %s" % (count, when)
        except PermissionError:
            return "PERMISSION DENIED (folder is there but cannot be listed)"
        except OSError as err:
            return "EXISTS  folder, cannot list (%s)" % err.strerror
    return "EXISTS  %s, changed %s" % (human_size(info.st_size), when)


def human_size(count):
    step = float(count)
    for unit in ("B", "KB", "MB", "GB"):
        if step < 1024 or unit == "GB":
            if unit == "B":
                return "%d B" % int(step)
            return "%.1f %s" % (step, unit)
        step /= 1024.0
    return "%d B" % count


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

def section_os():
    say("  system      : %s" % platform.system())
    say("  release     : %s" % platform.release())
    say("  platform    : %s" % platform.platform())
    say("  machine     : %s" % platform.machine())
    say("  working dir : %s" % tilde(Path.cwd()))
    say("  local time  : %s" % datetime.now().astimezone().isoformat(timespec="seconds"))


def section_python():
    say("  version     : %s" % platform.python_version())
    say("  executable  : %s" % tilde(sys.executable))
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    say("  virtual env : %s" % ("yes, at %s" % tilde(sys.prefix) if in_venv else "no"))
    if sys.version_info < (3, 9):
        say("  PROBLEM     : this Python is older than 3.9. Install a newer Python "
            "and run everything with that one.")
        note_failure("python")
    else:
        say("  status      : new enough")


def section_pip():
    try:
        import pip  # noqa: F401
        say("  import pip  : yes, version %s" % getattr(pip, "__version__", "unknown"))
    except Exception as err:
        say("  import pip  : NO (%s)" % err)
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=30)
        first = result.stdout.decode("utf-8", "replace").strip().splitlines()
        say("  pip runs    : exit %d%s" % (result.returncode,
                                           (", " + tilde(first[0])) if first else ""))
        if result.returncode != 0:
            say("  FIX         : reinstall pip with: %s -m ensurepip --upgrade"
                % tilde(sys.executable))
    except FileNotFoundError:
        say("  pip runs    : could not start this Python at all")
    except subprocess.TimeoutExpired:
        say("  pip runs    : timed out after 30 seconds (a slow or blocked network)")


def section_package():
    import importlib.util
    spec = None
    try:
        spec = importlib.util.find_spec("Whatsapp_Chat_Exporter")
    except Exception as err:
        say("  import test : failed to look for the package (%s)" % err)
    if spec is None:
        say("  package     : NOT installed for this Python")
        say("  FIX         : %s -m pip install \"whatsapp-chat-exporter[crypt15]==0.13.0\""
            % tilde(sys.executable))
        note_failure("exporter package")
    else:
        say("  package     : installed at %s" % tilde(getattr(spec, "origin", "unknown")))
        version = "unknown"
        try:
            from importlib import metadata
            version = metadata.version("whatsapp-chat-exporter")
        except Exception:
            pass
        say("  version     : %s (this skill is written against 0.13.0)" % version)

    command = shutil.which("wtsexporter")
    if command:
        say("  wtsexporter : on PATH at %s" % tilde(command))
    else:
        say("  wtsexporter : NOT on PATH")
    say("  best call   : %s   (works even when the command is not on PATH)"
        % PREFERRED_INVOCATION)
    say("  PATH        :")
    for entry in (os.environ.get("PATH") or "").split(os.pathsep):
        if entry:
            say("      %s" % tilde(entry))


def find_config(explicit):
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("WA_TRIAGE_CONFIG")
    if env:
        return Path(env).expanduser()
    roots = [Path.cwd(), Path.home() / ".config" / "whatsapp-triage"]
    for root in roots:
        for name in CONFIG_NAMES:
            candidate = root / name
            if candidate.exists():
                return candidate
    return None


def section_workdir(explicit, holder):
    path = find_config(explicit)
    if path is None:
        say("  config      : not found")
        say("  looked in   : the folder you are standing in, and %s"
            % tilde(Path.home() / ".config" / "whatsapp-triage"))
        say("  FIX         : run the setup step of the skill, which writes config.json.")
        note_failure("config file")
        return
    say("  config      : %s  (%s)" % (tilde(path), stat_line(path)))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        say("  parse       : FAILED, %s" % err)
        say("  FIX         : open that file and fix the JSON, usually a missing comma.")
        note_failure("config file")
        return
    if not isinstance(raw, dict):
        say("  parse       : FAILED, the file should hold a JSON object")
        note_failure("config file")
        return
    say("  parse       : ok, %d key(s)" % len(raw))
    holder["config"] = raw
    holder["config_path"] = path
    for key in sorted(raw):
        value = raw[key]
        if any(hint in key.lower() for hint in SECRET_HINTS):
            say("      %-14s = <hidden on purpose>" % key)
            continue
        if isinstance(value, (dict, list)):
            say("      %-14s = %d item(s)" % (key, len(value)))
            continue
        text = str(value)
        if os.sep in text or text.startswith("~"):
            resolved = Path(text).expanduser()
            if not resolved.is_absolute():
                resolved = (path.parent / resolved)
            say("      %-14s = %s  (%s)" % (key, tilde(resolved), stat_line(resolved)))
        else:
            say("      %-14s = %s" % (key, text))


def candidate_paths(holder):
    """Places worth looking, most specific first."""
    found = []
    config = holder.get("config") or {}
    config_dir = holder.get("config_path")
    if config_dir is not None:
        found.append(("working folder", Path(config_dir).parent))
    system = platform.system()
    if system == "Darwin":
        # The Mac app keeps its own plain SQLite store, and it does not care
        # which phone the user carries. Looked at before the phone backups
        # because it is the fast route when it is there.
        groups = Path.home() / "Library" / "Group Containers"
        found.append(("WhatsApp Desktop store",
                      groups / "group.net.whatsapp.WhatsApp.shared"))
        found.append(("WhatsApp Business Desktop store",
                      groups / "group.net.whatsapp.WhatsAppSMB.shared"))
        found.append(("iPhone backups",
                      Path.home() / "Library" / "Application Support" / "MobileSync" / "Backup"))
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            found.append(("iPhone backups",
                          Path(appdata) / "Apple Computer" / "MobileSync" / "Backup"))
            found.append(("iPhone backups (Store app)",
                          Path(appdata) / "Apple" / "MobileSync" / "Backup"))
    found.append(("Downloads", Path.home() / "Downloads"))
    found.append(("current folder", Path.cwd()))
    for key in ("export_path", "export", "contacts_db", "contacts", "backup_path",
                "source_path", "work_dir"):
        value = config.get(key)
        if isinstance(value, str) and value:
            resolved = Path(value).expanduser()
            if not resolved.is_absolute() and config_dir is not None:
                resolved = Path(config_dir).parent / resolved
            found.append(("config " + key, resolved))
    seen = set()
    unique = []
    for label, path in found:
        marker = str(path)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append((label, path))
    return unique


def section_candidates(holder):
    hits = []
    for label, path in candidate_paths(holder):
        state = stat_line(path)
        say("  %-26s %s" % (label + ":", tilde(path)))
        say("  %-26s %s" % ("", state))
        if state == "PERMISSION DENIED" or state.startswith("PERMISSION DENIED"):
            if platform.system() == "Darwin":
                if holder.get("mac_store") and "MobileSync" in str(path):
                    say("      not needed on the Mac Desktop route, the app's own "
                        "store above is the source. No grant required.")
                    continue
                say(FULL_DISK_ACCESS_REMEDY)
                note_failure("source access")
            continue
        if not state.startswith("EXISTS"):
            continue
        target = Path(path)
        if target.is_file():
            hits.append(target)
            continue
        try:
            entries = sorted(target.iterdir(), key=lambda item: item.name)
        except PermissionError:
            if platform.system() == "Darwin":
                if holder.get("mac_store") and "MobileSync" in str(target):
                    say("      not needed on the Mac Desktop route, the app's own "
                        "store above is the source. No grant required.")
                    continue
                say(FULL_DISK_ACCESS_REMEDY)
                note_failure("source access")
            continue
        except OSError:
            continue
        if "Group Containers" in str(target):
            # The live store, written to while WhatsApp runs. Report only the
            # two files the setup step copies, and never add them to the hits
            # the [db] section opens: the snapshot in the working folder is
            # what gets read. The other sixty odd files here are WhatsApp's
            # own bookkeeping and are nobody's business.
            for name in ("ChatStorage.sqlite", "ContactsV2.sqlite"):
                state = stat_line(target / name)
                say("      %-22s %s" % (name, state))
                if name == "ChatStorage.sqlite" and state.startswith("EXISTS"):
                    holder["mac_store"] = True
            continue
        if "MobileSync" in str(target):
            # Backup folders hold thousands of hash named files. Count them,
            # never walk them, and never print what is inside.
            backups = [item for item in entries if item.is_dir()]
            say("      %d backup folder(s)" % len(backups))
            for item in backups[:6]:
                say("        %s ... : %s" % (item.name[:8], stat_line(item)))
            continue
        for item in entries:
            lowered = item.name.lower()
            if item.name in INTERESTING_NAMES or lowered.endswith(".crypt15") \
                    or lowered.endswith(".crypt14"):
                say("      found %-22s %s" % (item.name, stat_line(item)))
                hits.append(item)
            elif lowered.endswith(".sqlite") or lowered.endswith(".db"):
                say("      found %-22s %s" % (item.name, stat_line(item)))
                hits.append(item)
    unique = []
    seen = set()
    for item in hits:
        try:
            marker = str(Path(item).resolve())
        except OSError:
            marker = str(item)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    holder["hits"] = unique
    hits = unique
    if not hits:
        say("  nothing usable found yet. That is normal before the first export.")


def describe_db(path):
    say("  %s" % tilde(path))
    connection = None
    try:
        connection = sqlite3.connect("file:%s?mode=ro" % Path(path).as_posix(), uri=True)
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    except Exception as err:
        say("      opens       : NO (%s)" % err)
        return False
    say("      opens       : yes, %d table(s)" % len(tables))
    shown = tables[:25]
    say("      tables      : %s%s" % (", ".join(shown),
                                      " ..." if len(tables) > len(shown) else ""))
    for table, column, kind in (("ZWAMESSAGE", "ZMESSAGEDATE", "apple"),
                                ("message", "timestamp", "millis"),
                                ("messages", "timestamp", "millis"),
                                ("ZWAADDRESSBOOKCONTACT", None, None),
                                ("ZWACHATSESSION", None, None)):
        if table not in tables:
            continue
        try:
            count = connection.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
        except Exception as err:
            say("      %-12s: count failed (%s)" % (table, err))
            continue
        line = "      %-12s: %d row(s)" % (table, count)
        if column and count:
            try:
                low, high = connection.execute(
                    "SELECT MIN(%s), MAX(%s) FROM %s" % (column, column, table)).fetchone()
                line += ", messages from %s to %s" % (stamp_text(low, kind),
                                                      stamp_text(high, kind))
            except Exception:
                pass
        say(line)
    try:
        connection.close()
    except Exception:
        pass
    return True


def stamp_text(value, kind):
    if value is None:
        return "unknown"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if kind == "apple":
        number += APPLE_EPOCH
    elif kind == "millis" and number > 1e11:
        number /= 1000.0
    try:
        return datetime.fromtimestamp(number).strftime("%Y-%m-%d")
    except (OverflowError, OSError, ValueError):
        return "unknown"


def section_db(holder):
    databases = [item for item in holder.get("hits", [])
                 if str(item).lower().endswith((".sqlite", ".db"))]
    if not databases:
        say("  no database file found yet, so there is nothing to open.")
        say("  This is the layer that comes from your phone backup, or on a Mac")
        say("  from the snapshot taken of the WhatsApp app's own store.")
        note_failure("message database")
        return
    opened = 0
    for path in databases:
        if describe_db(path):
            opened += 1
    if opened == 0:
        note_failure("message database")


def section_export(holder, explicit):
    config = holder.get("config") or {}
    path = None
    if explicit:
        path = Path(explicit).expanduser()
    else:
        for key in ("export_path", "export", "export_json"):
            value = config.get(key)
            if isinstance(value, str) and value:
                candidate = Path(value).expanduser()
                if not candidate.is_absolute() and holder.get("config_path"):
                    candidate = Path(holder["config_path"]).parent / candidate
                path = candidate
                break
    if path is None:
        for item in holder.get("hits", []):
            if item.name.lower().endswith(".json"):
                path = item
                break
    if path is None:
        say("  export      : no export JSON named anywhere yet")
        say("  NEXT        : run the export step, for example")
        say("                %s ..." % PREFERRED_INVOCATION)
        note_failure("export file")
        return
    say("  export      : %s" % tilde(path))
    say("  file        : %s" % stat_line(path))
    if not Path(path).exists():
        note_failure("export file")
        return
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8", errors="replace"))
    except Exception as err:
        say("  parses      : NO (%s)" % err)
        say("  FIX         : the export may be half written. Run the export again "
            "and let it finish.")
        note_failure("export file")
        return
    if not isinstance(data, dict):
        say("  parses      : yes, but the top level is not an object of chats")
        note_failure("export file")
        return
    newest = None
    messages = 0
    for key in data:
        chat = data[key]
        if not isinstance(chat, dict):
            continue
        container = chat.get("messages")
        if isinstance(container, dict):
            values = container.values()
        elif isinstance(container, list):
            values = container
        else:
            continue
        for message in values:
            if not isinstance(message, dict):
                continue
            messages += 1
            raw = message.get("timestamp")
            try:
                stamp = float(raw)
            except (TypeError, ValueError):
                continue
            if stamp > 1e11:
                stamp /= 1000.0
            if newest is None or stamp > newest:
                newest = stamp
    holder["export_ok"] = True
    say("  parses      : yes")
    say("  chats       : %d" % len(data))
    say("  messages    : %d" % messages)
    if newest is None:
        say("  newest      : unknown (no readable timestamp)")
    else:
        moment = datetime.fromtimestamp(newest)
        age = datetime.now() - moment
        say("  newest      : %s (%s old)" % (moment.strftime("%Y-%m-%d %H:%M"),
                                             short_age(age)))
        if age > timedelta(days=2):
            say("  NOTE        : that is more than two days old, so a fresh export "
                "would see more.")


def short_age(delta):
    hours = delta.total_seconds() / 3600.0
    if hours < 48:
        return "%.1f hours" % hours
    return "%.1f days" % (hours / 24.0)


def section_verdict(holder):
    failures = _state["failures"]
    if holder.get("export_ok"):
        # An export that parses is all the digest needs. A layer that only
        # matters for making the NEXT export is a note, not a blocker.
        say("  READY")
        say("  There is a usable export, so you can build the digest now:")
        say("    python3 wa_digest.py --config config.json")
        for layer in failures:
            say("  Note: %s is not working. That one matters the next time you refresh "
                "the export." % layer)
    elif failures:
        say("  SETUP INCOMPLETE AT %s" % failures[0])
        say("  Fix that layer first. The lines above it are fine, so start there,")
        say("  then run this doctor again.")
        for layer in failures[1:]:
            say("  Also not working yet: %s" % layer)
    else:
        say("  SETUP INCOMPLETE AT export file")
        say("  Nothing is broken, there is simply no export yet. Run the export step.")


# --------------------------------------------------------------------------

def build_parser():
    return_parser = argparse.ArgumentParser(
        prog="wa_doctor.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Check every step of the WhatsApp export setup and print one report.\n\n"
            "Run this when something is not working and you are not sure which part.\n"
            "It reads only. It changes nothing, and it never prints your messages,\n"
            "your contacts, or any password, so the whole report is safe to paste\n"
            "into a chat when you ask for help."),
        epilog=(
            "Usual run:\n"
            "  python3 wa_doctor.py\n\n"
            "Point it at a config that lives somewhere else:\n"
            "  python3 wa_doctor.py --config /path/to/config.json\n\n"
            "Copy everything it prints, from the first line to the last, and paste it\n"
            "in one go. A half report cannot be read."))
    return_parser.add_argument("--config", metavar="PATH",
                               help="the config.json to check. Found automatically when omitted.")
    return_parser.add_argument("--export", metavar="PATH",
                               help="the export JSON to check, if it is not the one in the config.")
    return return_parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    holder = {}
    say("WhatsApp triage doctor")
    say("Generated %s" % datetime.now().astimezone().isoformat(timespec="seconds"))
    say("Safe to paste: this report holds no message text, no contact names, no passwords.")

    run_section("operating system", "os", section_os)
    run_section("python", "python", section_python)
    run_section("pip", "pip", section_pip)
    run_section("exporter package", "package", section_package)
    run_section("config file", "workdir", section_workdir, args.config, holder)
    run_section("source access", "candidates", section_candidates, holder)
    run_section("message database", "db", section_db, holder)
    run_section("export file", "export", section_export, holder, args.export)
    head("verdict")
    section_verdict(holder)
    say()
    return 0


if __name__ == "__main__":
    sys.exit(main())
