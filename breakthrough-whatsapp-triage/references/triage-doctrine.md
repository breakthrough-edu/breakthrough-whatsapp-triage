# Triage doctrine

Loaded on every triage run, with `board-schema.md`. The digest carries no priority, band or urgency field on purpose: scripts count, you judge. This file is the judgement.

Three decisions, in order: which chats reach the board, which band each lands in, and what the draft says. Get the band slightly wrong and the user forgives you. Get the draft wrong and the board is worse than no board.

## What a real window actually looks like

Measured on a heavy account, on the default 3 day window: **61 conversations, 39 groups and 22 one-to-one**, 238 messages (175 inbound, 63 outbound), 38 unreadable attachments. At 7 days the same account gives 141 conversations and 1,043 messages, which is why 3 is the default and widening is the user's call.

Four consequences you must design around:

- **Most rows you consider are groups.** Even at 3 days it is 39 groups against 22 one-to-one. Group traffic is loud and almost never addressed to the user. The default verdict for a group is Parked, and you need a reason to move it.
- **The job is subtraction.** About 60 in, about 20 out, at most 5 of them urgent. A board where everything is urgent has failed.
- **There is no unread flag.** Confirmed absent from the export. Direction and recency are all you have. See `data-limits.md`.
- **You are reading a tail, not a thread.** `transcript` holds at most the last 20 messages (10 or 5 when the digest had to shrink to fit its byte budget), and each `text` is clipped at 240 characters with a trailing `…`. Never claim anything about how a conversation started.

## Step 1: read order

Even 60 chats do not all deserve your attention. Spend it in this order, and stop reading a chat the moment its band is decided.

1. `kind == "direct"` and `in_since_last_out >= 2`. Someone repeating themselves is the strongest live signal in the file. Read the whole transcript.
2. `kind == "direct"` and `last.direction == "in"`. Read the whole transcript.
3. `kind == "direct"` and `last.direction == "out"` and `last.hours_ago >= 48`. Read your own last message only, looking for an ask you made that was never answered.
4. `kind == "group"` and `in_since_last_out >= 1`. Skim the last 5 to 8 lines for the user's name, an @ mention, or a decision only the user can make. If none, stop. It is Parked.
5. `counts.in == 0`. Do not read. Not a row. Count it.

Chats the digest already pruned (`summary.pruned`) never reach you, but their counts still belong in `meta`.

## Step 2: who holds the ball

Mechanical, straight from fields:

- `last.direction == "in"`: they spoke last, ball with you.
- `in_since_last_out >= 1`: they have spoken since you last did. The count is how hard they are pushing.
- `last.direction == "out"` and `in_since_last_out == 0`: ball with them.
- **Override.** The ball comes back to you when your own last outbound asked for something or promised something, and either the date you named has passed or `last.hours_ago >= 72` with no reply. Waiting has stopped being a plan.

For groups this is not enough. A group is always talking, so `last.direction == "in"` means nothing there. In a group the ball is with the user only when the transcript shows an ask aimed at them: their name, an @ mention, a question only they can answer, or a decision the group is visibly stalled on. Otherwise the ball sits with the group.

## Step 3: the band ladder

First match wins. Evaluate top to bottom, stop at the first hit.

Band labels on the board: `高优先`, `在跑中`, `静置`. If the user's chats and instructions are English, use `Needs You`, `In Motion`, `Parked`. One language per board, no mixing.

**B1 → Needs You.** Ball with you, a live ask in the transcript, and one more day of silence costs something: money moves or stalls, a deadline slips, a dispute escalates, or a person is visibly waiting and getting sharper. Groups qualify only under the group rule above.

**B2 → Needs You.** Your own move is overdue. `last.direction == "out"`, you asked or promised, and the date you named has passed or `last.hours_ago >= 72` on a thread that matters. Nobody is going to remind you.

**B3 → Needs You.** `kind == "direct"` and `in_since_last_out >= 3`. Three unanswered inbound messages is the closest thing this export has to an unread flag. Board it even when the wording is polite, unless the transcript is plainly social chatter.

**B4 → In Motion.** A live thread whose next move is not yours today: you answered and are waiting, they named a date still in the future, or the deciding evidence sits inside a media gap that the user has to open on their phone before anyone can act.

**B5 → In Motion.** Ball with you and a real ask, but waiting a day costs nothing: a soft inquiry, a question with no deadline, a thank you that deserves a reply and nothing more.

**B6 → Parked.** Deserves a line but needs nothing: a closed loop (last inbound is thanks, ok, a sticker, a thumbs up), a broadcast or announcement group, team chatter someone else already handled, a dead vendor line, a group where all the traffic belongs to other people.

No match: not a row. Counted, never shown.

**A live ask** is something that changes what the user does: a question aimed at them, a request, a number to confirm, money, a decision, a deadline. **Not** a live ask: acknowledgements, FYI, forwards, a question another participant already answered, anything the user already answered further down the same transcript.

## Step 4: caps and overflow

| Band | Cap | Why |
|---|---|---|
| Needs You | 5 | More than five urgent things means nothing is urgent |
| In Motion | 8 | Past this the band becomes a to-read list |
| Parked | 7 | Enough to answer "did you miss anything loud" |
| Board total | 20 | The rail scrolls, the page does not. A board you scroll to see the top band is not a decision surface |

**Overflow never disappears.**

- More than 5 pass B1: rank by consequence, keep 5, move the rest to the **top of In Motion** with `tag.tone: "wf"`, and add `{"k": "Also needed you", "v": "2, top of In Motion"}` to `meta`.
- Parked overflow, and everything that never became a row: `{"k": "Scanned", "v": "61 chats, 20 on board"}` plus `{"k": "Not shown", "v": "41, no ask found"}`.
- Fold `summary.pruned` into that same "Not shown" number. Put `summary.truncated_chats` in `notice` instead, because truncation is a data gap and not a judgement of yours.

`meta` must always carry: the window (say the number of days, not just "recent"), a scanned/on board pair, and **exactly one** `hot: true` counter, which is the Needs You count. Rule 10 in `SKILL.md` also requires you to say the window in chat and offer to widen it, using `summary.beyond_window` for the real numbers.

## Step 5: tone

The orange rule, inherited from the template and not negotiable: **orange means next, needs you, and nothing else.** A second standing orange destroys the signal.

| Element | Needs You | In Motion | Parked |
|---|---|---|---|
| `tag.tone` | `accent` | `wf` | `ns` |
| `tag.label` | 要你动 / Needs you | 要盯 / Watching | 无待办 / Nothing to do |
| `chip.tone` | `accent` when the ball is with the user | `ns` always | `ns` always |
| gauge `hot` | the ball gauge, at most one | none | none |
| `dim` | false | false | `true` |
| `snippet` | required | required | omit |

- `accent` may not appear outside the first band, even on a row where the ball is genuinely with the user. In Motion says `球在你` in grey. The example board does exactly this, deliberately.
- **`bl` red** belongs to one case: a row that is on the board *because* something is unreadable, where triage cannot finish until the user opens their phone. Label it `读不到` / `Unreadable`, at most once per board. Ordinary media gaps use `flag: true` plus a `warn` box, not a red pill.
- **`dn` green** is applied automatically by the template to a link action button. Never author it in `tag.tone` or `chip.tone`, or green stops meaning "ready to send".
- **`flag: true`** on any row, in any band, where a media gap or a missing attachment touches evidence you relied on.

## Step 6: snippet

One line, rendered single line and ellipsised in a 376px rail. Budget about 40 CJK characters or 70 Latin.

The snippet is **the reason this chat is on the board**: the ask, then the friction.

- Good: `买 Pandan Wangi 收到 Kopi Tarik, 已经第三天没人回她`
- Good: `RM 8,940 的企业礼盒报价发出后静了 9 天`
- Good: `Asked for wholesale pricing, no idea yet what volume or where she resells`
- Bad: `3 new messages` (a count is not a reason)
- Bad: `Customer service issue` (a category is not a reason)
- Bad: `Needs a reply` (true of every row on the board)

Numbers pulled from the transcript earn their place: amounts, day counts, order numbers. Parked rows carry no snippet at all.

## Step 7: drafts

This is the product. Everything above is sorting.

**Two voice layers, and they answer different questions.** The counterpart's last five inbound messages decide WHICH language and register a draft is in (the mirroring rule below). The user's voice profile, when one exists, decides how THE USER sounds inside that register: their particles, their greetings and closers, their emoji habits, their usual length, in their own sampled sentences. Read the profile once per board, apply it to every draft, and where the two disagree the counterpart's language wins and the user's habits ride inside it. No profile means mirror-only, which is the original behaviour and still correct. ⛔ The profile never overrides the rules of this file: it shapes sound, never facts, commitments, or length caps.

**The profile itself** lives where `config.json`'s `tov_profile` points (default `tov-profile.md` in the working folder), is drafted from `wa_voice.py`'s corpus of the user's own sent messages, split direct versus group, and is ruled on by the user line by line before it is used. Stamp it with its derivation date; redraft only when the user asks.

**Mirror the language and register exactly.** Match the last five inbound messages from that person, not the majority language of the whole chat and never your own default. Malay stays Malay, Manglish stays Manglish, Chinese stays Chinese, and a code-switched chat stays code-switched in the same places. These users genuinely mix, in one sentence: `boss saya dah jumpa record, push kat finance hari ni` and `我要的是 pandan wangi wor` are both ordinary. Copy their particles (lah, wor, ya, ok), their loanwords, their form of address (Encik, 姐, boss, first name, or nothing at all), and their punctuation habits. Do not add particles they never use, do not upgrade a casual chat into formal Malay or corporate English, and never translate a person into your own language.

**Resolve the ask in the first sentence.** Sentence one answers, commits, apologises, declines, or asks the single question that unblocks everything. No warm-up, no "hope you are well", no restating their question back at them. On a complaint, sentence one takes responsibility before it explains anything, and it never blames a third party the user cannot verify.

**One draft, one purpose.** If three things are open, answer the one that unblocks the others and fold the rest into one closing line, or leave them for tomorrow. A numbered agenda of five items is not a WhatsApp message.

**Facts only from the transcript.** Every number, date, name, price, SKU, address and tracking number must appear in the transcript or in the user's own earlier messages. Everything else is a bracketed placeholder the user can scan and fill: `[price]`, `[the date you can actually ship]`, `[refund in full RM 268.90 / replace the two jars, pick one]`. A placeholder holding a real fork beats a confident guess every time. Say in `note` that the brackets are deliberate and which one needs a human.

**Propose, never commit.**

| Never write | Write instead |
|---|---|
| Payment received, thank you | I will check it against the account today and confirm |
| Yes, full refund of RM 268.90 | Once I see the photo we will [refund in full / replace the two jars], which would you prefer |
| Confirmed, Tuesday 3pm | Tuesday 3pm works on my side, confirming once I check [X] |
| No problem, RM 25 per unit | Price moves with volume, tell me the quantity and I will send you that tier |
| Sorry, the warehouse was overloaded | That is our mistake, and three days of silence made it worse |

The user's money, calendar and contracts are theirs. A draft may shape the reply. It may not sign it.

**Length.** One-to-one: 2 to 4 sentences, roughly 60 English words or 120 CJK characters. Group: 1 to 3 sentences. Hard calibration: **never longer than the longest message the user has written in that chat themselves.** A long apology reads like stalling. Emoji only if that chat already uses them, never as the opener.

**When the ask is unreadable.** If the load-bearing content is a voice note, an image, a document or an expired view once item, do not reason around it. The draft becomes one of two things: a short message asking them to resend or restate, or a shell with the decision bracketed. Then `note` says plainly that the draft is deliberately unfinished and why, the row gets `flag: true` and a `warn` block, and the gap gets its own line in `notice`. This is the most valuable honest move in the skill. Confident triage over a gap produces a wrong answer with a straight face.

**Never** mention the board, the digest, the export, or an AI. The draft has to read like the user typed it while walking.

**No draft at all** is the right answer for a Parked row. Either emit a draft block with `title` and `note` only (the template renders a clean empty state, and the note explains why nothing is owed), or omit `blocks` entirely for a row nobody will open. Both render fine, verified against the template's render loop.

## Step 8: action, label and hint

Read `reply_mode` and `href_prefix` from the digest. Never construct a number yourself.

**`reply_mode == "link"`**, one-to-one with a resolved number, 38 of 52 on the measured account:

```json
"action": {
  "type": "link",
  "label": "用草稿开启 WhatsApp",
  "label_dirty": "用你改的版本开启",
  "href_prefix": "<the digest's href_prefix, verbatim>",
  "hint": "<the one thing to check before pressing send>"
}
```

English board: `Open WhatsApp with this draft` and `Open with your edit`.

**`reply_mode == "copy"`**, every group plus the unresolved one-to-one chats, 14 of 52:

```json
"action": {
  "type": "copy",
  "label": "复制草稿",
  "label_dirty": "复制你改的版本",
  "hint": "群组没有号码可以开链接, 复制后自己贴进群里。"
}
```

English: `Copy draft`, `Copy your edit`, hint `WhatsApp has no link that opens a group with the text ready, so paste this into the group yourself.`

For an unresolved one-to-one: `这个对话 WhatsApp 把号码藏起来了, 所以没有链接可以开, 复制后自己贴。` English: `WhatsApp hides the number on this chat, so there is no link to open. Paste it in yourself.`

That hint is the only explanation most users will ever read. One sentence, states the reason, and does not sound like an apology or a bug, because it is a WhatsApp limitation and not a missing feature. Full story in `reply-links.md`.

The `hint` on a link row is **not** a restatement of the draft. It is the thing that will embarrass the user if they skip it: "check the warehouse can actually ship today before you promise it", "do not send with the brackets still in", "if nothing lands by Wednesday, open a ticket instead of asking him again".

A `copy` action must not carry `href_prefix`. The template branches on its presence, so a copy action with an href navigates instead of copying.

## Step 9: the notice strip

`notice` is how a gap stops being silent. Emit it when **any** of these holds, and set it to `null` only when none do:

- Any boarded row has a media gap you had to reason around (`counts.media_gaps > 0` on that chat).
- Any boarded row is `resolution: "unresolved"`, so it has no button.
- `summary.truncated_chats > 0`, or the digest degraded its transcripts (visible in `warnings`).
- `export.age_hours` is past the freshness threshold, so the board cannot see today.
- Zero rows reached Needs You. Say so, so a quiet board reads as a finding rather than a failure.

Shape:

- `badge`: `!`
- `title`: carries a count, for example `读不到的东西 · 4 项`
- `lead`: the single most consequential gap, in one sentence. This stays visible when the strip is collapsed, so the thing that could wreck a decision goes **here**, never buried in `items`.
- `items`: one line per gap, naming the chat, the date, the kind of thing, and what it probably held. `Farah Zulkifli, 08-17, 3 photos sent as view once, expired, unreadable`.
- `footer`: what to do about it (open that chat on the phone) plus the standing promise that nothing was guessed around it.

Copy every string in `digest.warnings` into `items` or the prose around it. They exist because the script already knows something you cannot see.

`legend` and `notice.footer` are injected as raw HTML. Write them yourself, keep them to your own words plus `<br>`, and never paste message content into either one.

## Before you emit

- Does every Needs You row cost the user something if ignored today? Any "not really" gets demoted.
- Exactly one orange element per row, exactly one hot counter in `meta`?
- Does every draft's first sentence resolve the ask?
- Is every number in every draft traceable to the transcript?
- Does every media gap appear in all three places (row `flag`, a `warn` block, `notice`)?
- Do scanned, on board and not shown add up against `summary.active_chats` and `summary.pruned`?
- Reading only the left rail, would the user know what today asks of them?
