# Data limits

Load this when the user asks where a conversation went, why voice notes are invisible, why a chat looks like it starts in the middle, or how big a window to run. Every limit here is a property of WhatsApp's own data, not a shortcoming of this skill, and saying so plainly is better than working around it quietly.

## The ceiling: only what the phone still holds

WhatsApp keeps message history on the device, not on a server it will hand back to you. The export contains what the phone still has, and nothing else.

Unrecoverable by this skill, by any other tool, and by WhatsApp support:

- Chats the user cleared or deleted.
- Messages that expired under disappearing messages.
- History lost across a phone migration, a restore from an older backup, or a switch between Android and iPhone. A chat can genuinely begin in the middle for this reason.
- View once photos and voice notes after they have been opened or expired. Gone on the phone too.
- Anything older than the retention the device itself kept.

If a chat looks truncated at the start, the honest answer is almost always this, not a bug in the export. Say so, and do not offer to dig deeper.

## There is no unread flag

**Confirmed by measurement: `read_timestamp` is `None` on all 1,090 messages of a 7 day window.** The export carries no unread marker, no delivery state, no "you have not opened this" signal of any kind.

Three consequences:

1. Triage is direction and recency based. Who spoke last (`last.direction`), how many inbound since the user last spoke (`in_since_last_out`), and how long ago (`last.hours_ago`). That is the whole toolkit. `triage-doctrine.md` is built on exactly those fields.
2. A chat the user already dealt with on their phone can still surface as Needs You, because nothing in the file says it was handled. The transcript is the only way to tell, which is why the doctrine reads transcripts before banding.
3. Never build a feature, a count or a claim on unread. Anything labelled "unread" on this board would be a fabrication.

System and protocol messages (group joins, setting changes, and similar) are skipped on purpose, so they never inflate a count. Messages with an unreadable timestamp are skipped too and reported in the digest's `warnings`.

## Media gaps

A media gap is a message whose content is a voice note, image, video, document, sticker or view once item that the export cannot turn into text. The digest marks the transcript row with a `media` label (usually the mime type) and an empty `text`, counts it in `counts.media_gaps` per chat and `summary.media_gaps` overall.

**Measured: 210 gaps in a 7 day window.**

Why this matters more here than in email triage: in real business chat the ask often *is* the voice note or the photo. A five minute voice note holding the actual complaint is invisible to the session. A payment screenshot is a number you cannot read. A quotation PDF appears as a filename and nothing else.

**The rule: never let a gap pass silently.** Every gap that touches evidence you relied on shows up in three places: `flag: true` on the row, a `warn` block in the panel, and a line in the `notice` strip. A gap you name is handled. A gap you skip quietly produces confidently wrong triage, which is worse than no triage at all, because the user acts on it.

## You are reading a tail, and a clipped one

Two more limits inside the digest itself:

- `transcript` holds at most the **last 20 messages** of a chat, dropping to 10 or 5 when the digest has to shrink to fit its byte budget. A 200 message group gives you its last handful.
- Each message `text` is clipped at **240 characters** with a trailing `…`. A long message can end mid sentence.

So: never state anything about how a conversation began, and treat a clipped message as an incomplete quote. Put the honesty on the board itself, in the `读取窗` gauge: `41 条读到 40 条`, `8/16 起 (前段未读)`.

The digest also drops whole chats before you see them, and says so in `summary.pruned`: `broadcast` (WhatsApp broadcast pseudo chats), `ignored` (`ignored_jids` in config), `empty_window` (nothing at all in the window). If the whole digest is still over budget, the quietest chats by last activity are left out entirely and counted in `summary.truncated_chats`, with a matching line in `warnings`. Those counts belong in the board's `meta`, and truncation belongs in `notice`.

## Choosing a window

Measured on one real heavy library of 72,776 messages:

| Window | Active chats | Messages | Digest size |
|---|---|---|---|
| 3 days | 66 | 271 | 24 KB |
| 7 days | 147 raw, 143 real | 1,090 | 76 KB |
| 30 days | 455 | 5,444 | 358 KB |

- **3 days** is a Monday morning or daily pass. Comfortable, fast, and the transcripts stay long because the budget is not under pressure.
- **7 days** is the default and the weekly clear out. Still readable in one session at full transcript depth.
- **30 days is too big to use raw.** It needs aggressive pruning before it fits, and pruning is exactly what costs you transcript depth, so you end up reading five message tails of 455 chats. It is also the wrong shape for the question: triage answers "what needs me now", not "what happened last month". If a user insists, expect `pruned` and `truncated_chats` to be non-zero and declare both in `notice`.

Two notes on the numbers. The window is measured backwards from the moment of the run, so the chat count moves a little between runs as the edge slides. And a lighter account scales down roughly in proportion; these figures are an upper bound, not a norm.

**Composition matters more than volume.** On the 7 day window, the split was **91 groups and 52 one-to-one**, with **747 inbound and 343 outbound** messages. Most of what you read is group traffic addressed to nobody in particular. Budget your reading accordingly, as `triage-doctrine.md` step 1 sets out.

## Freshness

The digest reports `export.age_hours`, measured against the newest message in the whole export. Past the threshold (48 hours by default) it emits a warning, because a board built on a stale export will confidently tell the user that a resolved thread still needs them. When that happens, give the user the plain date their data stops at and offer the refresh ritual before building anything.

## Where all this lives

The export, the digest and the board are files on the user's own computer, in their working folder. The board is a single offline HTML file: it loads no external resources, calls no server, and phones nothing home. No message is ever sent, and nothing is uploaded, posted or transmitted anywhere.

The one thing worth stating plainly rather than glossing: the digest is read by the Claude session doing the triage, exactly the same way anything pasted into a conversation is read. That is what makes the judgement possible. The raw export never enters the session at all, only the windowed digest. A user who would rather a particular conversation not be read should add its JID to `ignored_jids` or narrow the window before the digest is built, and the skill should offer that as soon as they hesitate.
