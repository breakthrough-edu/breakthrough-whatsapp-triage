---
name: breakthrough-whatsapp-triage
description: Turns an overwhelming WhatsApp backlog into a one-page daily action board with a ready-to-edit draft reply for each conversation that actually needs the user today. Everything stays on their machine, and nothing is ever sent automatically. Use when the user wants their WhatsApp triaged ("triage my whatsapp", "help me clear whatsapp", or complaining about hundreds of unread chats), wants the one-time export set up ("set up whatsapp export"), asks for an update later the same day or to refresh a board built on a stale export, asks to look further back or pull in one older conversation ("go back a week", "show me the last month"), wants the drafts to sound like them ("set up my tone profile", "update my tone profile"), hits a run that failed and needs diagnosing, or asks why the board behaves the way it does (why a row copies instead of opening, where a conversation or voice note went). The read window stays narrow by default and widens only on the user's explicit ask.
---

# breakthrough-whatsapp-triage

Read this file first, every time. It routes and it forbids. It does not carry procedures, those live in the files it points at, and when this file disagrees with one of them the specific file wins and you fix this one in the same session.

## The ten rules

These hold in every mode. Breaking one is a bug, not a judgement call.

1. **The raw export never enters your context.** It is tens of megabytes. Only the scripts open it. If a digest comes back too big, narrow the window or drill with `--include-jid`. Never open `export.json`.
2. **Nothing is ever sent.** Buttons build a link or copy text. The skill never drives WhatsApp, never sends, and never marks anything as replied. The last action is always the user's.
3. **Every draft is a proposal.** Facts come only from the transcript. Anything the user must supply stays a bracketed placeholder like `[price]`. Never invent a number, a date, or a promise.
4. **Never fabricate a phone number.** A link button is legal only when the digest resolved a real number. Groups always copy. Unresolved chats always copy. WhatsApp has no link that opens a group with prefilled text, this is structural and no amount of trying will find one.
5. **The template is read-only.** All board changes go through the board JSON and `wa_board.py`. Never hand-edit `assets/triage-board.html`.
6. **During setup, a step is done when its probe says so**, not when the user says it worked. Ask for pasted output every time.
7. **Everything stays on this computer.** Never upload, post, or transmit the export, the digest, or the board. Never ask the user to paste their Android encryption key into the chat.
8. **House style for everything the skill emits**, board copy and drafts included: no em dashes, no double hyphens, no spaced hyphens as separators. Commas, colons, periods, parentheses.
9. **Scripts compute facts, you make judgements.** Never hand-parse epochs or JIDs, and never ask a script to decide what is urgent.
10. **Read narrow by default, widen only when asked.** The window is **3 days**. Never widen it on your own initiative, not to be helpful, not because the board looked thin, not because the user seemed busy. Every extra day pulls more of someone's private life into this session, and that has to be their call, said out loud.

## The window, and the sentence you must always say

3 days is the default because it is the smallest window that still answers "what needs me today". On a heavy account it reads about 60 conversations instead of about 140, and roughly a quarter of the messages a week would.

After every board, tell the user in one plain sentence:

- the window you used and the date it reaches back to,
- how many conversations were on the board,
- how many were left out because nothing happened in them inside the window, and how recently the most recent of those spoke, both of which are in `summary.beyond_window`,
- that they can ask for more, for example "go back a week" or "show me the last month".

Say it in their language, in their register, and keep it to a sentence or two. It is an offer, not a disclaimer.

Two things it must never become. Do not read the wider window first and then ask, the point is that the data was never pulled. And do not turn it into a nag: mention it once per board and drop it.

When they do ask for more, rerun with `--days N` and say what the wider window added. If they want one specific old conversation rather than a wider sweep, use `--include-jid` instead, which is narrower and pulls in far less.

## Routing

Look for `config.json` in the working folder (default `~/Documents/WhatsApp-Triage/`, on Windows the equivalent under the user profile).

**Missing, or `setup_complete` is false, or the user asks to set up**
Go to SETUP. Read `setup/00-overview.md` and follow it. Never improvise a setup step that is not written down. When the files run out, switch to the protocol in `setup/troubleshooting.md` rather than guessing.

**Present and complete**
Run `wa_digest.py --config <config>`.

- Nonzero exit, run `wa_doctor.py` and enter the troubleshooting protocol.
- Exit 0 but the export is stale (`age_hours` past the threshold, default 48), tell the user the plain date their data stops at and offer the refresh ritual at the bottom of their platform's setup file. If the export ends before the window even opens, refuse to build a board of ghosts and say why.
- Exit 0 and `boards/` already holds a board for today: this is an UPDATE, not a first build. The export is a snapshot, so if it has not been re-exported since that board was built, a rerun would redraw the same data and call it fresh. Say so in one plain sentence ("your data still stops at <time>; updating means a re-export first, a few minutes") and offer the refresh ritual. Only rebuild on the same export if the user says they want it anyway. After any same-day rebuild, read the earlier board's JSON first and open your report with what changed against it: which conversations are new to the board, which dropped off. The diff is what an afternoon rerun is actually for. ⛔ Same-day board files never overwrite: the second board of the day is `board-<date>-2.json` / `.html`, the third `-3`, matching the promise below that nothing is ever overwritten.
- Otherwise go to TRIAGE.

**TRIAGE**
Read `references/triage-doctrine.md` and `references/board-schema.md`, then the digest file. If a voice profile exists (the `tov_profile` path in `config.json`, else `tov-profile.md` in the working folder), read it before writing a single draft; the doctrine's drafts step says how it layers with per-chat mirroring. No profile is not a problem: mirror-only is the original behaviour, and the profile is a sharpener, never a prerequisite. Sort the chats, write the drafts, author the board JSON, run `wa_board.py`, open the result.

**VOICE PROFILE, on ask ("set up my tone profile", "update my tone profile")**
Run `wa_voice.py --config <config>`; it samples the user's own sent messages into `voice-corpus.json` (counts on stdout, content only in the file). Read the corpus, draft or redraft the profile per the doctrine's drafts step, and show it to the user whole: it is their voice, they rule on every line. On first creation ask where it should live, default `tov-profile.md` beside the config; whatever they choose, record the path as `tov_profile` in `config.json`. Stamp the profile with today's date. ⛔ Never regenerate it unasked, and never let it override the ten rules: it shapes how drafts sound, not what they may claim or commit.

Then **always say the window out loud and offer to widen it.** This is required, not a nicety, and it is rule 10 below.

Load `references/reply-links.md` when the user asks why a row copies instead of opening, or when a link misbehaves. Load `references/data-limits.md` when they ask where a conversation went, or why voice notes are invisible.

## What the user is actually paying you for

Not the export, that is plumbing. The value is the judgement: out of a few hundred conversations, which handful genuinely need them today, and what should they say. A board where everything is urgent has failed. So has a board of tidy summaries that leaves the user still deciding.

Two failure modes to watch in yourself. The first is triaging on volume, a loud group is rarely the thing that matters and a single quiet message asking for a price usually is. The second is confident triage over an unreadable gap: when the actual ask sits inside a voice note or an image the export cannot read, say so rather than reasoning around it. `references/data-limits.md` explains why that gap exists, and the board's notice strip is where it gets declared. A gap you name is handled. A gap you skip quietly is the one that produces a wrong answer with a straight face.

## Working folder

The skill directory holds code and doctrine only. Everything belonging to the user lives in the working folder and must survive a reinstall.

```
~/Documents/WhatsApp-Triage/
  config.json          platform, paths, window, ignored chats, freshness stamps, tov_profile
  export.json          the raw export, large, never opened by you
  tov-profile.md       how the user sounds, drafted from their own messages, user-ruled
  voice-corpus.json    wa_voice.py's sample behind the profile, regenerated on ask
  digests/             digest-<date>-<N>d.json
  boards/              board-<date>.json and board-<date>.html (same day again: -2, -3)
```

Digests and boards are date-stamped, never overwritten, never auto-deleted. The user may want to look back at what last Monday actually demanded of them.
