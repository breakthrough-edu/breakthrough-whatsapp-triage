---
name: whatsapp-triage
description: Turns an overwhelming WhatsApp backlog into a one-page daily action board. The first run walks the user through a one-time export of their WhatsApp history onto their own computer, from an Android backup file or an iPhone local backup. Every later run filters that export to a recent window, works out which conversations actually need the user today, and generates an offline HTML triage board carrying a ready-to-edit draft reply for each one. Use when the user says triage my whatsapp, whatsapp backlog, whatsapp board, build my triage board, refresh my board, set up whatsapp export, help me clear whatsapp, or complains about hundreds of unread chats and not knowing where to start. Everything stays on their machine and nothing is ever sent automatically.
---

# whatsapp-triage

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
- Otherwise go to TRIAGE.

**TRIAGE**
Read `references/triage-doctrine.md` and `references/board-schema.md`, then the digest file. Sort the chats, write the drafts, author the board JSON, run `wa_board.py`, open the result.

Then **always say the window out loud and offer to widen it.** This is required, not a nicety, and it is rule 10 below.

Load `references/reply-links.md` when the user asks why a row copies instead of opening, or when a link misbehaves. Load `references/data-limits.md` when they ask where a conversation went, or why voice notes are invisible.

## What the user is actually paying you for

Not the export, that is plumbing. The value is the judgement: out of a few hundred conversations, which handful genuinely need them today, and what should they say. A board where everything is urgent has failed. So has a board of tidy summaries that leaves the user still deciding.

Two failure modes to watch in yourself. The first is triaging on volume, a loud group is rarely the thing that matters and a single quiet message asking for a price usually is. The second is confident triage over an unreadable gap: when the actual ask sits inside a voice note or an image the export cannot read, say so rather than reasoning around it. `references/data-limits.md` explains why that gap exists, and the board's notice strip is where it gets declared. A gap you name is handled. A gap you skip quietly is the one that produces a wrong answer with a straight face.

## Working folder

The skill directory holds code and doctrine only. Everything belonging to the user lives in the working folder and must survive a reinstall.

```
~/Documents/WhatsApp-Triage/
  config.json          platform, paths, window, ignored chats, freshness stamps
  export.json          the raw export, large, never opened by you
  digests/             digest-<date>-<N>d.json
  boards/              board-<date>.json and board-<date>.html
```

Digests and boards are date-stamped, never overwritten, never auto-deleted. The user may want to look back at what last Monday actually demanded of them.
