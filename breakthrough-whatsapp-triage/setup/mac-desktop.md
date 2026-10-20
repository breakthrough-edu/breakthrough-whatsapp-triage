# Mac Desktop branch

End state: a snapshot of the WhatsApp Mac app's own database sitting in the working folder, and `export.json` built from it. No cable, no phone backup, about two minutes.

**Who this is for: anyone whose computer is a Mac with the WhatsApp app installed and signed in. The phone does not matter.** Android or iPhone, the Mac app keeps its own copy of the history on the Mac, in a plain unencrypted SQLite database, and that copy is what this branch reads. An Android user on a Mac belongs here, not in `android.md`. Do not route them to the phone out of habit.

Prerequisite: `computer-prep.md` finished, including its Step 7 probe for this route. Every `python3` below means whichever word you settled on for this machine, though on a Mac it is almost always `python3` as written.

**No Full Disk Access grant is expected on this branch.** Measured 2026-08-29 from a terminal that had none: the WhatsApp folder listed fine while the iPhone backup folder and Messages were both refused. If Step M1 comes back `Operation not permitted` on some machine anyway, the grant recipe in `computer-prep.md` Step 7 is the fix, but do not ask for it up front. It is a large permission to hand over for a route that has not asked for it.

## What is known about this path, and what is not

Measured end to end on a real Mac, 2026-08-29, WhatsApp Mac app 26.28.75:

| | |
|---|---|
| Snapshot of the live database | 0.3 seconds, 74 MB |
| Export to JSON | 1.2 seconds, 32 MB |
| What came out | 73,723 messages, 1,350 conversations: full history for the year before the Mac was linked, plus a scattered handful of older messages reaching back years |

This is the one route in this skill that has been run end to end, more than once, on a real machine. Say that plainly if the user asks how much to trust it. It is also the reason this branch has fewer honesty caveats than the two phone branches, not a sign that it was tested less.

**The one thing not to promise: years of history. The Mac's copy holds about one year.** When the Mac app is linked, the phone sends it roughly the last year of messages, then the Mac keeps everything that arrives after that. WhatsApp's own description of linked devices matches: they receive up to one year of chat history. Anything older comes across only as scattered leftovers, a few stray messages in some old conversations and rarely more than a dozen in any one. So the oldest date in the Mac's copy can sit years back while the real history starts about a year before the day the Mac was linked. On the measured machine the oldest message was from 2014, yet complete history began exactly 365 days before the link.

Two consequences. Never read the oldest date as depth, and never tell anyone their years of history are on the Mac. And for anything older than about a year, the phone is the only source: an iPhone backup through `iphone.md`, or the phone's own database through `android.md`. For triage none of this matters, since the window is days, not years. Expect the same limit whichever phone they carry, and let Step M4 confirm it on the machine in front of you.

## Step M1: confirm the app's database is there

```
ls -lh ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite
```

**Good output** is one line with a size in the tens or hundreds of megabytes and a recent date.

| What came back | Conclusion |
|---|---|
| a file of tens of MB or more, dated today or recently | this branch works, go to Step M2 |
| `Operation not permitted` | unexpected on this route, see the note above, then `computer-prep.md` Step 7 |
| `No such file or directory` | the Mac app is not installed, or has never been signed in, see the routing note below |
| a file of a few hundred KB, or dated months ago | the app is installed but was signed out or never finished its first sync, ask them to open WhatsApp, sign in, leave it open until the chat list has filled, then rerun this probe |

**If the file is genuinely absent**, do not start improvising. Two honest options, and the user picks:

- **Install the WhatsApp app on this Mac and sign in.** It is on the Mac App Store, and signing in means opening WhatsApp on the phone and scanning the code the Mac shows. The first sync takes a few minutes and the chat list fills in as it goes. Then rerun Step M1. This is usually far faster than the phone route, and it leaves them something useful afterwards.
- **Go to the phone route** instead, `android.md` or `iphone.md`, per their phone.

Linking a device is a real change to their WhatsApp account, so offer it, do not do it for them, and do not push if they would rather not.

**WhatsApp Business users:** the Business Mac app keeps its own separate folder, `group.net.whatsapp.WhatsAppSMB.shared`, with the same filenames inside. Run the same probe against that path. This variant has not been measured, so treat every step below as expected behavior with the probe attached, and add `--business` to the export command in Step M3.

## Step M2: take a snapshot, do not read the live file

The app is running and writing while we work. A plain copy of a database that is being written to gives you a file that is missing whatever is still sitting in its write ahead log, which shows up much later as a board that mysteriously stops a few hours short. SQLite's own backup command takes a consistent copy of a live database, so use that, and it does not require quitting WhatsApp.

Both commands are one line each, run from the working folder:

```
cd ~/Documents/WhatsApp-Triage
sqlite3 ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite ".backup './ChatStorage.sqlite'"
sqlite3 ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ContactsV2.sqlite ".backup './ContactsV2.sqlite'"
```

`sqlite3` ships with macOS, so there is nothing to install. Both commands print nothing at all when they succeed, which is normal and is worth saying before they run, since silence reads as failure to most people.

**Probe:**

```
ls -lh ChatStorage.sqlite ContactsV2.sqlite
```

**Good output** is two lines, `ChatStorage.sqlite` in the tens or hundreds of megabytes and `ContactsV2.sqlite` usually under a few megabytes, both dated within the last minute.

| What came back | Conclusion |
|---|---|
| both files, plausible sizes, timestamped now | continue to Step M3 |
| `unable to open database file` | the source path is wrong or unreadable, reread it against Step M1 before touching permissions |
| `ChatStorage.sqlite` of 0 bytes | the source path was wrong or the command was cut short, rerun the exact line |
| `command not found: sqlite3` | unexpected on macOS, go to `troubleshooting.md` rather than installing anything |

`ContactsV2.sqlite` is worth having: it is what turns `@lid` style chats into real phone numbers later, which decides whether those rows get a reply link or a copy button. If it genuinely will not copy, the run still works, so continue and leave `contacts_db` out of the config in Step M5.

## Step M3: export

```
python3 -m Whatsapp_Chat_Exporter -i -d ChatStorage.sqlite -j export.json --no-html
```

Three things about that line:

- `-i` is the iOS flag, and it is correct here even when the phone is an Android. The Mac app stores its messages in the same Core Data shape iOS uses, so this is the reader that fits the file. Nothing about this flag touches or asks about the phone.
- `-d` points at the snapshot in the working folder, never at the file inside the app's own folder. Do not let the tool near the live database.
- **Never add `-m`.** That tells the tool to copy the media folder, which on the measured machine was 7.1 GB of photos and video. It buys nothing here: the export is text either way, and unreadable attachments are handled on the board as declared gaps, see `references/data-limits.md`.

**WhatsApp Business app:** add `--business`.

**Good output ends with:**

```
[INFO] Processed <a number> messages in less than a second
[INFO] JSON file saved...(<some size>)
[INFO] Everything is done!
```

Two lines in that output surprise people, and neither is a fault:

- `Copying media directory...` appears even without `-m`. Without the flag it copies only the small vCards folder, which took under a second and 200 KB on the measured machine. If it instead sits there for minutes and the folder is growing, the `-m` flag got in somehow, stop it and rerun the line exactly as written.
- Two folders appear in the working folder afterwards, `AppDomainGroup-group.net.whatsapp.WhatsApp.shared/` and `result/`. They hold those vCards and nothing else. Harmless, and safe to delete any time.

Ask for the full paste including the typed command. Do not open `export.json` to check it, and do not write a one liner that reads it. It is tens of megabytes and it must never enter your context. The doctor reports what you need.

## Step M4: prove it, then say how far back it really goes

```
python3 wa_doctor.py
```

Run it from this skill's `scripts/` folder, or give the full path.

Good output:

- `[candidates]` shows the WhatsApp Desktop store as `EXISTS` with a recent date, and the working folder holding both snapshots.
- `[db]` opens `ChatStorage.sqlite`, reports `ZWAMESSAGE` with a row count and a date range, then a `per year` line and a `dense from` line.
- `[export]` reports `parses : yes`, `chats` and `messages` above zero, and `newest` dated today.

**Do not quote the oldest date in `[db]` as the answer.** On this route it is usually one of the scattered leftovers described at the top of this file, not the start of the history. The two lines under it find the real start, from the snapshot in the working folder, with counts only and no message text. `per year` shows the shape: a run of years in the tens or low hundreds, then a sudden year in the thousands. `dense from` names the month where that jump happens, the first month of the unbroken run of busy months that reaches today, and counts the leftovers before it. The shape, with invented numbers:

```
      ZWAMESSAGE  : 69060 row(s), messages from 2016-02-11 to <today>
      per year    : 2016: 9,  2017: 41,  2018: 63,  2019: 88,  2020: 152,  2021: 20497
                    2022: 48210
      dense from  : 2021-03 (estimate), every month since holds 400 or more; the 353 message(s) before it are scattered leftovers
```

| What `dense from` says | Conclusion |
|---|---|
| a month about a year before they linked the Mac, with leftovers counted before it | expected, this is the normal shape |
| `the oldest month`, and that month is years back | more than this file expects, say what you see and move on |
| `the oldest month`, within the last year or so | a recently linked Mac with no leftovers, it is what the Mac holds |
| `cannot tell` | a light account, too few messages a month to separate history from leftovers. Read the `per year` line for the jump by eye, and if there is none, say how far back the busy years go |

**That start point is the ceiling conversation, and it belongs to the user, not to you.** Tell them in one plain sentence that their Mac holds their full history from about that point, roughly a year before it was linked, plus a few stray older messages. Then let them react. For triage, which reads the last few days, that is the whole conversation. If they want anything older, it is not a fault and nothing on the Mac can deepen it: the phone holds it, and the phone route is the way to reach it, an iPhone backup through `iphone.md` or the phone's database through `android.md`. Offer that as a choice, not as a failure, and only if the older history actually matters for what they asked for.

## Step M5: write the config file, which is what marks setup as done

Write it yourself, in the working folder next to `export.json`. Do not make the user type JSON. This exact shape is the one running on the measured machine.

```json
{
  "version": 1,
  "setup_complete": true,
  "platform": "macos",
  "source": "whatsapp-desktop-local-db",
  "export_path": "export.json",
  "contacts_db": "ContactsV2.sqlite",
  "days": 3,
  "link_style": "app",
  "ignored_jids": []
}
```

- `platform` and `source` are recorded for the humans reading this folder later. The digest ignores both, so they cost nothing and they tell the next session which route this machine is on.
- `contacts_db` must name the file that is actually there. Check the working folder rather than trusting Step M2, since a missing contacts database is silent: the digest still builds, it just marks those chats unresolved.
- `link_style` is `app` here. This branch already proved the WhatsApp Mac app is installed, so reply links have something to open.
- `days` is the triage window, 3 by default and deliberately narrow. The user widens it by asking, and the skill offers that after every board.

**Probe:**

```
python3 wa_doctor.py
```

Good output: `[workdir]` names the config file instead of reporting `not found`, and `[verdict]` no longer says `SETUP INCOMPLETE`. That verdict line is the single check that setup is genuinely finished.

## The privacy floor on this branch, worth one sentence

The snapshot is a complete plaintext copy of every conversation, sitting in a folder of their choosing. Nothing is uploaded and nothing leaves the Mac. Unlike the phone routes there is no password and no encryption key anywhere in this path, so nothing sensitive should ever end up in the chat window.

Say one more thing, because it is a genuine advantage here: deleting the snapshot costs nothing, since Step M2 remakes it in under a second. If they want the plaintext copy gone between runs, `rm ChatStorage.sqlite ContactsV2.sqlite export.json` in the working folder is the whole cleanup, and the next refresh rebuilds all three.

## Refresh ritual

This is the part they repeat, and on this branch it is the whole of it. Give it to them once setup succeeds, as three lines they can save:

```
cd ~/Documents/WhatsApp-Triage
sqlite3 ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite ".backup './ChatStorage.sqlite'"
python3 -m Whatsapp_Chat_Exporter -i -d ChatStorage.sqlite -j export.json --no-html
```

Seconds, not minutes. WhatsApp can stay open. The contacts snapshot only needs retaking when they have added contacts, so it is left out of the short form on purpose.

**The one rule to state plainly:** the board reads the export, not WhatsApp. Skipping the re-snapshot means rebuilding this morning's board out of yesterday's data, and it will look fresh while being wrong. Any run that matters starts with these three lines.
