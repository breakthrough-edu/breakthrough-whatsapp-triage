#!/usr/bin/env python3
"""Put a finished board of decisions into the offline HTML template.

One job: take the JSON a session produced, check it against the rules the
template actually enforces, and write a single self contained HTML file with
that JSON dropped into the one block the template reads.

What this script must NEVER do:
  * write to the template. The template is read only, always. Output goes to
    the file named by --out.
  * touch any byte of the template other than the inside of the
    <script id="board-data"> block.
  * write a half checked file. Validation runs first. If anything is wrong,
    nothing is written and every problem is printed at once, so one pass of
    fixing is enough.
  * let message text break the page. Every "</" inside the JSON is escaped to
    "<\\/", because a chat message containing "</script" would otherwise end
    the block early and blank the page. JSON reads "\\/" as "/", so the data
    is unchanged.

Two fields are different, and the difference is deliberate. The template runs
every string through its own escaper except two: legend, and notice.footer.
Those two land in the page as raw HTML, which is what makes "J K to move<br>"
work. Both are written by whoever builds the board, never lifted from a
message, so raw is safe by design. This script checks that anyway: those two
fields may carry only a short list of formatting tags, and anything that could
run code is refused. Do not remove that check on the grounds that the input is
trusted, because the whole point is that trust gets verified once, here.

Standard library only. Python 3.9 and newer.
"""

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_TEMPLATE = 2
EXIT_INVALID = 3
EXIT_WRITE = 4

TONES = ("accent", "wf", "ns", "bl", "dn")
BLOCK_KINDS = ("prose", "list", "draft")
MAX_BLOCKS = 3
MAX_ROWS_COMFORTABLE = 30
ACCENT_SHARE_WARN = 0.40

# Orange means "next, needs you". The template only lets it mean that in two
# places, so anywhere else is a mistake, not a style choice.
ACCENT_PATH_RE = re.compile(r"^bands\[\d+\]\.rows\[\d+\]\.(tag|chip)\.tone$")

HREF_RE = re.compile(r"^(whatsapp://send\?phone=\d{6,15}&text=|https://wa\.me/\d{6,15}\?text=)$")

# legend and notice.footer are written into the page as raw HTML by the
# template. Only these tags are allowed there, and nothing that can run.
RAW_HTML_FIELDS = ("legend", "notice.footer")
RAW_ALLOWED_TAGS = ("br", "b", "i", "span", "code")
TAG_RE = re.compile(r"<\s*/?\s*([A-Za-z][A-Za-z0-9]*)")

# Row ids become element ids and land inside a quoted CSS selector.
ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
DANGEROUS_RE = (
    (re.compile(r"<\s*script", re.IGNORECASE), "a <script tag"),
    (re.compile(r"<\s*iframe", re.IGNORECASE), "an <iframe tag"),
    (re.compile(r"javascript\s*:", re.IGNORECASE), "a javascript: URL"),
    (re.compile(r"\bon\w+\s*=", re.IGNORECASE), "an inline event handler such as onclick="),
)

OPEN_TAG_RE = re.compile(
    r"<script\b[^>]*\bid\s*=\s*[\"']board-data[\"'][^>]*>", re.IGNORECASE)
CLOSE_TAG_RE = re.compile(r"</script\s*>", re.IGNORECASE)


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

class Report(object):
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, reason):
        self.errors.append((path, reason))

    def warn(self, message):
        self.warnings.append(message)


def walk_tones(node, path, report):
    """Every key named tone, anywhere in the data, has to be a legal tone."""
    if isinstance(node, dict):
        for key in node:
            child_path = "%s.%s" % (path, key) if path else str(key)
            if key == "tone":
                value = node[key]
                if not isinstance(value, str) or value not in TONES:
                    report.error(child_path,
                                 "tone must be one of %s, found %r"
                                 % (" / ".join(TONES), value))
                elif value == "accent" and not ACCENT_PATH_RE.match(child_path):
                    report.error(child_path,
                                 "tone \"accent\" is only allowed on a row tag or a row chip. "
                                 "Orange marks the one thing that needs the reader, so a second "
                                 "orange anywhere else kills the signal. Use wf, ns, bl or dn.")
            walk_tones(node[key], child_path, report)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            walk_tones(item, "%s[%d]" % (path, index), report)


def validate_raw_html(value, path, report):
    """Guard the two fields the template prints without escaping.

    They exist so a person can write "J K to move<br>Enter to fire". They are
    author written, never taken from a message, and this keeps it that way.
    """
    if value is None:
        return
    if not isinstance(value, str):
        report.error(path, "must be a string of plain text, with at most simple "
                           "formatting tags (%s)" % ", ".join(RAW_ALLOWED_TAGS))
        return
    for pattern, description in DANGEROUS_RE:
        if pattern.search(value):
            report.error(path,
                         "holds %s. This field is written into the page as real HTML, not as "
                         "text, so anything that can run is refused here. Keep it to words and "
                         "these tags: %s." % (description, ", ".join(RAW_ALLOWED_TAGS)))
            return
    for match in TAG_RE.finditer(value):
        name = match.group(1).lower()
        if name not in RAW_ALLOWED_TAGS:
            report.error(path,
                         "uses the tag <%s>. This field is written into the page as real HTML, "
                         "so only these tags are allowed: %s. Everything else belongs in a "
                         "block, where the template escapes it for you."
                         % (name, ", ".join(RAW_ALLOWED_TAGS)))
            return


def validate_block(block, path, report):
    if not isinstance(block, dict):
        report.error(path, "a block must be an object")
        return None
    kind = block.get("kind")
    if kind not in BLOCK_KINDS:
        report.error(path + ".kind",
                     "kind must be one of %s, found %r" % (" / ".join(BLOCK_KINDS), kind))
        return None
    if kind == "list":
        items = block.get("items")
        if items is not None and not isinstance(items, list):
            report.error(path + ".items", "items must be a list of strings")
    if kind == "draft":
        action = block.get("action")
        if action is None:
            return kind
        if not isinstance(action, dict):
            report.error(path + ".action", "action must be an object")
            return kind
        kind_of_action = action.get("type")
        href = action.get("href_prefix")
        if kind_of_action not in ("link", "copy"):
            report.error(path + ".action.type",
                         "type must be \"link\" or \"copy\", found %r" % kind_of_action)
        elif kind_of_action == "link":
            if not isinstance(href, str) or not HREF_RE.match(href):
                report.error(path + ".action.href_prefix",
                             "a link action needs href_prefix in exactly one of these shapes: "
                             "whatsapp://send?phone=<6 to 15 digits>&text=  or  "
                             "https://wa.me/<6 to 15 digits>?text=  . Found %r. "
                             "Groups and hidden contacts have no such link, so use "
                             "type \"copy\" for them instead of inventing a number." % href)
        elif kind_of_action == "copy":
            if href is not None:
                report.error(path + ".action.href_prefix",
                             "a copy action must not carry href_prefix. Remove it, or "
                             "change type to \"link\".")
    return kind


def validate_row(row, path, report, seen_ids):
    if not isinstance(row, dict):
        report.error(path, "a row must be an object")
        return False
    row_id = row.get("id")
    if not isinstance(row_id, str) or not row_id.strip():
        report.error(path + ".id", "id must be a non empty string, it is what pairs the "
                                   "left list with the right panel")
    elif not ID_RE.match(row_id):
        # The template builds a CSS selector by pasting the id into a quoted
        # string, so a space or a quote inside it breaks the action button.
        report.error(path + ".id",
                     "id %r has characters that break the page. The id is pasted straight "
                     "into an element id and a selector, so use letters, digits, hyphens "
                     "and underscores only. The house style is lowercase with hyphens, "
                     "for example quote-thread-stalled." % row_id)
    else:
        if row_id in seen_ids:
            report.error(path + ".id", "id %r is already used by %s. Row ids must be unique, "
                                       "otherwise two rows fight over the same panel."
                         % (row_id, seen_ids[row_id]))
        else:
            seen_ids[row_id] = path
    if not isinstance(row.get("name"), str) or not row.get("name").strip():
        report.error(path + ".name", "name must be a non empty string")

    blocks = row.get("blocks")
    if blocks is None:
        blocks = []
    if not isinstance(blocks, list):
        report.error(path + ".blocks", "blocks must be a list. Leave it out, or use [], "
                                       "for a row with nothing to show.")
        return is_accent(row)
    if len(blocks) > MAX_BLOCKS:
        report.error(path + ".blocks",
                     "%d blocks, the layout holds at most %d. The page does not scroll, "
                     "so the extra ones would be pushed out of sight."
                     % (len(blocks), MAX_BLOCKS))
    drafts = 0
    for index, block in enumerate(blocks):
        kind = validate_block(block, "%s.blocks[%d]" % (path, index), report)
        if kind == "draft":
            drafts += 1
    if drafts > 1:
        report.error(path + ".blocks",
                     "%d draft blocks, only one is allowed. The draft block owns the whole "
                     "right hand column, so a second one has nowhere to go." % drafts)
    return is_accent(row)


def is_accent(row):
    tag = row.get("tag")
    return isinstance(tag, dict) and tag.get("tone") == "accent"


def validate(data, report):
    if not isinstance(data, dict):
        report.error("$", "the board data must be a JSON object")
        return
    walk_tones(data, "", report)

    bands = data.get("bands")
    if bands is None:
        report.error("bands", "bands is missing. Even one band is fine: "
                              "\"bands\": [{\"label\": \"...\", \"rows\": []}]")
        return
    if not isinstance(bands, list):
        report.error("bands", "bands must be a list of sections")
        return

    seen_ids = {}
    total_rows = 0
    accent_rows = 0
    for band_index, band in enumerate(bands):
        band_path = "bands[%d]" % band_index
        if not isinstance(band, dict):
            report.error(band_path, "a band must be an object with label and rows")
            continue
        if not isinstance(band.get("label"), str) or not band.get("label").strip():
            report.error(band_path + ".label", "label must be a non empty string")
        rows = band.get("rows")
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            report.error(band_path + ".rows", "rows must be a list")
            continue
        for row_index, row in enumerate(rows):
            total_rows += 1
            if validate_row(row, "%s.rows[%d]" % (band_path, row_index), report, seen_ids):
                accent_rows += 1

    notice = data.get("notice")
    if notice is not None and not isinstance(notice, dict):
        report.error("notice", "notice must be an object, or null to hide the whole strip")
    elif isinstance(notice, dict):
        validate_raw_html(notice.get("footer"), "notice.footer", report)

    validate_raw_html(data.get("legend"), "legend", report)

    meta = data.get("meta")
    if meta is not None and not isinstance(meta, list):
        report.error("meta", "meta must be a list of {k, v} pairs")

    if total_rows == 0:
        report.warn("The board has no rows at all. The page will open and say so, "
                    "which is fine when there really was nothing to triage.")
    if total_rows > MAX_ROWS_COMFORTABLE:
        report.warn("%d rows. Above about %d the left list stops being scannable, which is "
                    "the whole point of the board. Consider a shorter window or a tighter cut."
                    % (total_rows, MAX_ROWS_COMFORTABLE))
    if total_rows and (accent_rows / float(total_rows)) > ACCENT_SHARE_WARN:
        report.warn("%d of %d rows are tagged accent (%.0f percent). Orange is supposed to mean "
                    "\"this one needs you now\". When most of the page is orange it means "
                    "nothing." % (accent_rows, total_rows, 100.0 * accent_rows / total_rows))


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def encode_payload(data):
    """JSON for embedding inside a <script> block.

    The "</" escape is not optional. Chat text is whatever other people typed,
    and one message containing "</script" would close the block and blank the
    page. JSON treats "\\/" as a plain slash, so nothing about the data changes.
    """
    text = json.dumps(data, ensure_ascii=False, indent=1, separators=(",", ":"))
    return text.replace("</", "<\\/")


def comment_spans(text):
    """Every <!-- ... --> range, so a mention inside a comment is not mistaken
    for the real block. The shipped template documents itself by quoting the
    board-data tag inside a comment, and that quote comes first in the file."""
    spans = []
    cursor = 0
    while True:
        start = text.find("<!--", cursor)
        if start < 0:
            break
        end = text.find("-->", start + 4)
        if end < 0:
            spans.append((start, len(text)))
            break
        spans.append((start, end + 3))
        cursor = end + 3
    return spans


def inside(spans, position):
    return any(start <= position < end for start, end in spans)


def find_block(template_text):
    """Return (inner_start, inner_end) of the real board-data block."""
    spans = comment_spans(template_text)
    fallback = None
    for opening in OPEN_TAG_RE.finditer(template_text):
        if inside(spans, opening.start()):
            continue  # a mention in the documentation, not the block itself
        closing = CLOSE_TAG_RE.search(template_text, opening.end())
        if not closing:
            continue
        bounds = (opening.end(), closing.start())
        if fallback is None:
            fallback = bounds
        current = template_text[bounds[0]:bounds[1]].strip()
        try:
            json.loads(current)
        except Exception:
            continue  # holds something that is not JSON, keep looking
        return bounds
    return fallback


def splice(template_text, payload):
    bounds = find_block(template_text)
    if bounds is None:
        return None, ("could not find the <script id=\"board-data\" "
                      "type=\"application/json\"> block in the template. Use the template "
                      "that ships with this skill, unchanged.")
    start, end = bounds
    return template_text[:start] + "\n" + payload + "\n" + template_text[end:], None


# --------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="wa_board.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Build the offline triage board: one HTML file you can double click.\n\n"
            "It takes your board JSON, checks it against the rules the page relies on,\n"
            "and writes a finished HTML file. The template itself is never modified.\n"
            "Nothing is uploaded and nothing is sent: the page only ever builds a link\n"
            "for you to press."),
        epilog=(
            "Usual run:\n"
            "  python3 wa_board.py --data board.json \\\n"
            "      --template assets/triage-board.html --out board.html\n\n"
            "Build it and open it straight away:\n"
            "  python3 wa_board.py --data board.json \\\n"
            "      --template assets/triage-board.html --out board.html --open\n\n"
            "Exit codes: 0 written, 2 the template is missing or is the wrong file,\n"
            "3 the data broke a rule and nothing was written, 4 the file could not be saved."))
    parser.add_argument("--data", required=True, metavar="PATH",
                        help="the board JSON to put into the page.")
    parser.add_argument("--template", required=True, metavar="PATH",
                        help="assets/triage-board.html. Read only, never written to.")
    parser.add_argument("--out", required=True, metavar="PATH",
                        help="where to save the finished HTML.")
    parser.add_argument("--open", action="store_true",
                        help="open the finished file in your browser once it is written.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    template_path = Path(args.template).expanduser()
    if not template_path.exists():
        sys.stderr.write("Template not found: %s\n"
                         "Point --template at assets/triage-board.html inside this skill.\n"
                         % template_path)
        return EXIT_TEMPLATE
    try:
        template_text = template_path.read_text(encoding="utf-8")
    except Exception as err:
        sys.stderr.write("Template could not be read: %s\n" % err)
        return EXIT_TEMPLATE

    data_path = Path(args.data).expanduser()
    report = Report()
    data = None
    if not data_path.exists():
        report.error("--data", "file not found: %s" % data_path)
    else:
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception as err:
            report.error("--data", "not valid JSON: %s. Usually a missing comma, "
                                   "a trailing comma, or a stray quote." % err)
    if data is not None:
        validate(data, report)

    if report.errors:
        sys.stderr.write("Nothing was written. %d problem(s) in %s:\n\n"
                         % (len(report.errors), data_path))
        for path, reason in report.errors:
            sys.stderr.write("  %s\n      %s\n" % (path or "$", reason))
        sys.stderr.write("\nFix all of them, then run this again.\n")
        return EXIT_INVALID

    payload = encode_payload(data)
    rendered, problem = splice(template_text, payload)
    if rendered is None:
        sys.stderr.write("%s\n" % problem)
        return EXIT_TEMPLATE

    out_path = Path(args.out).expanduser()
    if out_path.resolve() == template_path.resolve():
        sys.stderr.write("Refusing to write on top of the template. Choose another --out.\n")
        return EXIT_WRITE
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    except Exception as err:
        sys.stderr.write("Could not save %s: %s\n"
                         "Pick a folder you can write to with --out.\n" % (out_path, err))
        return EXIT_WRITE

    rows = sum(len(band.get("rows") or [])
               for band in (data.get("bands") or []) if isinstance(band, dict))
    print("Wrote %s (%s, %d row(s))"
          % (out_path, human_size(len(rendered.encode("utf-8"))), rows))
    for message in report.warnings:
        print("Warning: %s" % message)
    if args.open:
        try:
            import webbrowser
            webbrowser.open(out_path.resolve().as_uri())
        except Exception as err:
            print("Could not open a browser (%s). Double click the file instead." % err)
    return EXIT_OK


def human_size(count):
    step = float(count)
    for unit in ("B", "KB", "MB"):
        if step < 1024 or unit == "MB":
            if unit == "B":
                return "%d B" % int(step)
            return "%.1f %s" % (step, unit)
        step /= 1024.0
    return "%d B" % count


if __name__ == "__main__":
    sys.exit(main())
