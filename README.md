# breakthrough-whatsapp-triage

A Claude Code skill that turns an overwhelming WhatsApp backlog into a one page action board.

Most of us have a WhatsApp list with a few hundred conversations and no way to tell which three of them actually need us today. This skill reads your own exported history, works out where the ball is genuinely in your court, and builds a local board with a ready to edit draft reply for each one.

## Install

```bash
npx skills add breakthrough-edu/breakthrough-whatsapp-triage
```

Then say "set up whatsapp export" to Claude Code and it walks you through the one time setup.

## How it works

1. **Once**, you export your WhatsApp history onto your own computer, from an Android backup file or an iPhone local backup. Claude walks you through it and debugs alongside you when your machine does something the guide did not predict.
2. **Every run after that**, a script filters that export down to the last **3 days**, Claude reads the result and decides what needs you, and you get an offline HTML board.

The 3 day default is deliberate. It is the smallest window that still answers "what needs me today", and it keeps the amount of your private conversation that any AI session ever sees as small as it can be while still being useful. After every board you are told what the window covered and what it left out, and you can widen it whenever you want by just asking.

One to one conversations get a button that opens WhatsApp with the draft already in the box. Groups get a copy button instead, because WhatsApp has no link that opens a group with prefilled text.

## What it does not do

- **It never sends anything.** Buttons build a link or copy text. The last action is always yours.
- **It never leaves your computer.** No upload, no API, no account linking, no third party service.
- **It cannot recover what your phone no longer holds.** An export contains what is still on the device. Chats cleared years ago, or lost in a phone migration, are gone, and no tool brings them back.
- **It does not read WhatsApp live.** It reads a snapshot you took, so refreshing means taking a new one.

## Requirements

- Python 3.10 or newer
- `whatsapp-chat-exporter` 0.13.0, which the setup step installs
- Your phone, a cable, and about half an hour the first time

## Privacy

The export is every one of your conversations in plain text, sitting in a folder you chose. Nothing is transmitted anywhere, and the drafting happens against a filtered digest rather than the full archive. Treat the folder the way you would treat your phone.

## License

MIT

This skill directs an AI agent running on your machine to read and modify your own files. Review what it proposes before approving it, keep backups of anything you care about, and note that everything here is provided as is, without warranty of any kind (see LICENSE).
