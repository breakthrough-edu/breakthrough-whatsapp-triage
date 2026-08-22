# Troubleshooting

Load this only when a probe has actually failed. It is written to you, the session, not to the user.

Two of the three paths in this skill have never been run end to end on a real phone. You will meet symptoms nobody wrote down. Section A is how to navigate those by reasoning. Sections B and C are the shortcuts for the ones that were catalogued.

---

# Section A: the protocol

## A0. First move, always: the doctor

Before any hypothesis, before any question, before any fix:

```
python3 wa_doctor.py
```

(It ships in this skill's `scripts/` folder. Run it from there, or give the full path. Use their Python word.)

One paste replaces ten questions. It reports the whole stack at once, so you stop guessing which layer to interrogate. Read it with Section B.

If the doctor itself will not run, that is not a dead end, it is data: it means the failure is at the Python layer or the location layer, and it narrows the search before you have asked anything.

## A1. Get evidence, not adjectives

**Never ask "did it work?"** Ask for everything the terminal printed, including the line they typed.

The typed line is half the diagnosis. Users retype commands with a lost quote, a smart quote from a chat app, a wrong folder, a lowercase package name, or a different command than the one you sent. If you only see the error, you will debug a command that was never run.

When a paste arrives without the typed line, ask again for that one line before reasoning. It costs one message and saves several.

## A2. Symptom, hypothesis, discriminating probe, fix

Work in that order, out loud, one cycle at a time.

- **Symptom:** the exact text from the paste, not your paraphrase of it.
- **Hypothesis:** one specific cause you can state as a claim about this machine, for example "pip installed into a different Python than the one running the command".
- **Discriminating probe:** a command whose result comes out differently depending on whether the hypothesis is true. If both outcomes leave you believing the same thing, it is not a probe, it is busywork. Do not send it.
- **Fix:** only after the probe confirms. Then rerun the original failing command as the verification, not a different one.

**Change one thing at a time.** If you change two and the symptom moves, you have learned nothing and you cannot go back.

## A3. Unknown symptom protocol

For a symptom that is not in Section C, do not pattern match against something that looks similar. Locate the broken layer first.

The stack, in order, with the doctor block that reports each one:

1. OS, `[os]`
2. Python, `[python]` and `[pip]`
3. Package, `[package]`
4. File location, `[workdir]` and `[candidates]`
5. File permission, `[candidates]`
6. File format, `[db]`
7. Tool, `[export]`

**Exactly one of these broke first.** Everything below a broken layer produces junk symptoms, and chasing those is how sessions get lost.

Binary search it rather than walking all seven. Start at layer 4, file location, because it splits the stack evenly and the doctor reports it plainly:

- **Layer 4 is broken** (the expected file is not where the command says): the fault is at layer 4 or above. Check layers 2 and 3 next. Do not touch permissions or formats yet.
- **Layer 4 is healthy** (the file exists exactly where the command points): the fault is at 5, 6 or 7. Check permission, then format, then the tool.

The doctor's own `[verdict]` block usually hands you the answer outright, so read that first. Use this ladder when the verdict is clean but something is still wrong, or when the doctor cannot run.

Then state the layer you landed on before proposing anything. "The file is in the right place and readable, but its first bytes are not a crypt15 header, so this is a format problem, not a permission problem" is a diagnosis. "Let us try reinstalling" is not.

## A4. Three strikes, then change the route

**After three failed hypotheses on one symptom, stop.** Do not start a fourth cycle, do not reinstall anything, do not go wider.

Instead, do these three things in one message:

1. **Summarize the machine state** in plain language: OS and version, Python word and version, package version, which files exist where, which layer you got to, and which three hypotheses were eliminated and by what evidence. Write it so it is useful if the user comes back tomorrow or on another machine.
2. **Propose the alternate route** rather than more debugging:
   - **A different computer.** Most often the fastest real fix, especially for iPhone on Windows. A machine that already has Finder or Apple Devices working, or a household Windows PC, skips the whole broken layer.
   - **A different backup style.** Android: an older `msgstore.db.crypt14` file already sitting in the Databases folder, which the tool also reads. iPhone: an unencrypted backup instead of fighting a forgotten encryption password.
   - **A narrower export.** WhatsApp's own per chat "Export chat" produces a text file, and the tool reads that with `-e`. It is one conversation at a time and manual, so it is a fallback, not the plan, but for a user who only needs their three busiest chats it beats an abandoned setup.
3. **Say plainly that setup is paused, not failed,** and name what would unblock it. Users forgive a stuck setup. They do not forgive an hour of silent flailing.

## A5. Standing rules while debugging

- **Never ask for the 64 digit key.** Not to "check the format", not partially. The Android command is built so the key goes into a hidden prompt on their own machine.
- **Never ask for message content, contact names, or a screenshot of chats.** Counts, sizes, dates, filenames and error text answer every question in this file.
- **Never propose upgrading the exporter** to fix a symptom. The pin at `0.13.0` is what keeps the exported JSON shape stable for the rest of the skill. If you truly believe a version bug is the cause, say so and stop, do not upgrade under the user.
- **Do not add permissions or reinstall broadly** to make a symptom go away. A machine changed in ways nobody tracked is worse than a machine with a known fault.

---

# Section B: reading `wa_doctor.py`

The doctor prints one block per layer, in this order, then a verdict:

```
[os]  [python]  [pip]  [package]  [workdir]  [candidates]  [db]  [export]  [verdict]
```

Its own header says it is safe to paste: it carries no message text, no contact names and no passwords. So ask for the whole report, not an excerpt. The user editing it down is how the useful line goes missing.

**Read `[verdict]` first.** It names the first layer that failed, in the form `SETUP INCOMPLETE AT <layer>`, and tells you the blocks above it are fine. Believe it and start there. Then **stop at the first unhealthy block going down**, because everything below a broken layer produces junk symptoms.

The doctor also prints its own `FIX` and `NEXT` lines. They are usually right, with one exception noted below.

| Block | Healthy looks like | If it is not healthy |
|---|---|---|
| `[os]` | system, release, and a `working dir` | a `working dir` that is not the working folder is the cheapest bug here, have them `cd` there and rerun everything |
| `[python]` | `status : new enough`, one `executable` path | anything below 3.10 cannot install the tool, go to `computer-prep.md` Step 3 |
| `[pip]` | `import pip : yes`, `pip runs : exit 0` | no pip means that interpreter is unusable, reinstall Python rather than fighting it |
| `[package]` | the package present for this Python at 0.13.0 | `NOT installed for this Python` while the user insists pip succeeded is the two Pythons problem, see C2.1. A version other than 0.13.0 means an unpinned install, reinstall the pin |
| `[workdir]` | the config file is found | before the config step of the phone branch, `not found` is expected, see the false alarms below |
| `[candidates]` | the expected input listed as `EXISTS` with a plausible size and a recent date | `PERMISSION DENIED` on macOS is Full Disk Access, and the doctor prints the full recipe itself. A file that is 0 bytes or a few kilobytes means a failed copy, redo the transfer |
| `[db]` | `opens : yes`, a table list, and row counts with a date range | `opens : NO` means the file is not a database, usually a truncated copy or a still encrypted file |
| `[export]` | `parses : yes`, `chats` and `messages` above zero, `newest` dated today | `parses : NO` means a half written export, rerun it. A `newest` date well in the past means the export never actually reran |

## Four false alarms in this report, do not chase them

1. **`[workdir] config : not found` during setup.** The config file is written at the end of the phone branch, so until then this block fails and `[verdict]` reads `SETUP INCOMPLETE AT config file`. That is the expected state mid setup, not a fault. It only matters after the config step.
2. **`wtsexporter : NOT on PATH` in `[package]`.** Informational. These docs never use that command, and the `best call` line the doctor prints next to it is the form to use.
3. **`[db]` finding nothing on the iPhone branch.** That block only opens files whose names end in `.sqlite` or `.db`. On iPhone the extracted message database has a long hash filename with no extension, so an empty `[db]` is normal there. Judge the iPhone branch by `[export]`.
4. **The `[package]` FIX line omits the crypto extra.** It suggests the plain pinned install. On Android that produces a decryption failure one step later. Use the form from `computer-prep.md` Step 5 instead, with `[crypt15]` included.

## Two comparisons worth making by eye

- **The `[python] executable` path against the pip location in `[pip]`.** Different installations means the two Pythons problem, found without asking the user anything.
- **Dates across blocks.** An `[export] newest` older than the backup date in `[candidates]` means the export did not rerun, which explains a whole class of "the data is wrong" reports without any deeper digging.

---

# Section C: symptom table

Match on the exact text in the paste. Where two causes share one symptom, the discriminating probe is the whole point of the row, so run it before fixing.

| Symptom in the paste | Most likely cause | Discriminating probe | Fix once confirmed |
|---|---|---|---|
| `'wtsexporter' is not recognized` or `command not found: wtsexporter` | the short command is not on PATH, common on Windows | `python3 -m Whatsapp_Chat_Exporter --help` | use the `-m` form everywhere, this is why these docs never lead with the short alias |
| `Python was not found`, or the Microsoft Store opens | Python missing, or the Store alias is shadowing it | `py -3 --version` | if `py -3` answers, use it as their Python word, otherwise install per `computer-prep.md` Step 3 with Add to PATH ticked |
| `No module named Whatsapp_Chat_Exporter`, but pip said it installed | two Pythons, pip went to a different interpreter | compare `python3 -m pip show whatsapp-chat-exporter` `Location:` with the interpreter path in the doctor | reinstall with `python3 -m pip install`, see C2.1 |
| `No module named pip` | that interpreter has no pip | `python3 -m ensurepip --version` | on Windows reinstall Python with the default options, on macOS use the python.org build |
| `Could not find a version that satisfies the requirement` | Python older than 3.10 | `python3 --version` | install a current Python, `computer-prep.md` Step 3 |
| `Operation not permitted` listing MobileSync (macOS) | Full Disk Access not granted, or granted without a real quit | `ls ~/Library/Application\ Support/MobileSync/Backup/` after a full quit and reopen | see C2.2, the quit is the step people skip |
| `You don't have permission to access the backup database` from the tool | same, seen from inside the tool | as above | as above, do not chase this as a missing file |
| `You don't have the dependencies to handle encrypted backup` | either a genuinely encrypted backup, or a folder that is not a backup at all | list the folder, is there a `Manifest.db` and is it 0 bytes | 0 bytes or absent means wrong folder, pick the right one. Real backup means install the decrypt package, `iphone.md` Step I7 |
| `Essential WhatsApp files are missing from the iOS backup` | WhatsApp's own end-to-end encrypted backup is on, or it is the Business app | ask what WhatsApp Settings, Chats, End-to-end encrypted backup shows, and which app they use | Business app, add `--business`. Otherwise turn that WhatsApp setting off, make a fresh device backup, rerun |
| `The message database does not exist. You may specify the path to database file with option -d` | the `-b` path is wrong, or the backup held nothing | paste the exact command line, then list that path | correct the path, quote it if it has spaces, rerun |
| MobileSync folder empty, or newest backup is months old | the phone backs up to iCloud, not to this computer | in Finder or Apple Devices, read the Backups setting back | switch to backing up to this computer, then Back Up Now, `iphone.md` Step I3 |
| phone never appears in Finder, iTunes or Apple Devices | cable without data lines, Trust prompt not accepted, or Apple software not installed | unlock the phone and replug, does a Trust prompt appear | accept Trust with passcode, try another cable, on Windows install the Apple Devices app |
| `Failed to decrypt backup: incorrect password?` | wrong backup password, often the Apple ID password or phone passcode by mistake | ask which password they typed | the iTunes or Finder backup password only. If lost, turn encryption off in Step I3 and make a fresh backup |
| `Decryption/Authentication failed. Ensure you are using the correct key.` | key does not match this database file | check that the crypt15 file date is after the key was created | see C2.3 |
| `Crypt15 is not supported`, or `Dependencies of decrypt_backup ... are not present` | crypto extra missing | `python3 -m pip show pycryptodome javaobj-py3` | reinstall with `python3 -m pip install "whatsapp-chat-exporter[crypt15]==0.13.0"` |
| `Unknown backup format. The backup file must be crypt12, crypt14 or crypt15` | the filename lost its extension in the copy | `ls` or `dir` in the working folder, read the exact filename | rename it back so it ends in `.crypt15`, the tool reads the crypt version from the name |
| `Brute-forcing offsets` then a long wait | it is a crypt14 file, not crypt15 | read the filename | let it run, it often succeeds. Cleaner fix is to redo `android.md` Step A1 for a crypt15 backup |
| Android has no `Databases` folder at the old top level path | newer Android and WhatsApp moved it | look in `Android/media/com.whatsapp/WhatsApp/Databases/` | use the new path, `Android/data/` is blocked and is not where to look |
| export succeeds, but far fewer messages than expected | the ceiling, the phone no longer holds that history | ask when they last switched phones, reinstalled WhatsApp, or cleared chats | not a bug, do not debug it, see C2.4 |
| the digest reports zero messages in the window | `export.json` is stale, the export never actually reran | compare the modification date of `export.json` against the backup date | rerun the refresh ritual from the phone branch |
| the digest crashes on an unexpected field shape | tool version drift, an unpinned or upgraded install | rerun the digest with `--dump-bad 3`, and `python3 -m pip show whatsapp-chat-exporter` | reinstall the pin `==0.13.0` and re-export, this is exactly what the pin exists to prevent |
| link buttons in the output do nothing when clicked | WhatsApp Desktop is not installed, so the desktop link scheme has nothing to open | ask whether the WhatsApp desktop app is installed and opens | set the config `link_style` to `web` |
| `Copying media directory...` sits there for many minutes | it is duplicating the media tree, which can be gigabytes | check the size of the output folder twice, a minute apart, is it growing | it is working, wait. If space is tight, rerun with `-c` to move instead of copy |
| `JSONDecodeError` reading `export.json` | the export was interrupted, so the file is truncated | check the file size, and whether the run ever printed `Everything is done!` | rerun the export, do not try to repair the file |

## C2: the four fixes that need more than one line

### C2.1 The two Pythons

Symptom: pip reports a successful install, the tool is not found. Cause: `pip` and `python3` on this machine belong to different installations, so the package is genuinely installed, just not where the command is looking.

Never debug this by reinstalling with a bare `pip`, which is what caused it. The fix is always to route both through the same interpreter:

```
python3 -m pip install "whatsapp-chat-exporter[crypt15]==0.13.0"
python3 -m Whatsapp_Chat_Exporter --help
```

Confirm with the `Location:` line from `python3 -m pip show whatsapp-chat-exporter`. It must sit inside the same installation as the interpreter path the doctor reported. If the user has been experimenting, ask them to close the terminal and open a new one before rerunning, since a stale window can carry an old PATH.

### C2.2 macOS Full Disk Access

Symptom: `Operation not permitted`, or the tool's own permission message. It is a real, reproduced restriction, not a broken file.

The recipe is in `computer-prep.md` Step 7. When it has already been tried and the symptom persists, the failure is almost always step 4 of that recipe:

- Closing the window is not quitting. They must quit the terminal application itself (Command Q, or right click the Dock icon and Quit), then open it fresh.
- The switch must be on for the app they actually use. Someone who granted access to Terminal but runs commands in iTerm still gets denied, and so does someone running commands inside a code editor's built in terminal.

Probe after a genuine quit and reopen, from a new window:

```
ls ~/Library/Application\ Support/MobileSync/Backup/
```

If it still fails, stop and go to A4. Do not start granting other permissions.

### C2.3 Android key mismatch

`Decryption/Authentication failed. Ensure you are using the correct key.` means the key and the file do not belong together. In order of likelihood:

1. **They typed it wrong.** The prompt is hidden, so typos are invisible. Have them rerun and paste the key in from where they saved it rather than typing it. Spaces in the key are fine, the tool ignores them.
2. **The file predates the key.** Turning WhatsApp's encrypted backup off and on generates a new key, and old database files stay locked to the old one. Fix by making a fresh backup (`android.md` Step A2) and copying the new file over.
3. **They are holding a password, not a key.** A 64 character string of digits and the letters a to f is a key. Anything shorter or with other characters is a password, which this path cannot use. Redo Step A1 and choose the 64 digit key option.

Ask them to confirm the length is 64 characters. **Do not ask them to show you the key, and do not accept it if they offer.** If a key does land in the chat anyway, tell them plainly that it should now be treated as exposed, and that turning encrypted backup off and on in WhatsApp issues a new one.

### C2.4 The export is much smaller than expected

This is usually not a bug, and it is a conversation rather than a fix. Handle it directly.

First confirm the export is complete, not truncated: the run printed `Everything is done!`, and the chat count is plausible even if the message count is low.

Then say what happened, without defensiveness: the export contains everything the phone still holds, and history that was cleared, or lost in a phone switch or a WhatsApp reinstall, was never on the phone to export. No tool recovers it, and there is no better tool to try. This is why `00-overview.md` says it before the first command.

What is genuinely worth checking before accepting a small number:

- Were contact names missing too, making chats look empty? On Android, adding `--wab wa.db.crypt15` recovers names, see `android.md` Step A7.
- Did the export run against an old backup? Compare dates, see the stale export row above.
- Are they expecting group history from before they joined? That never existed on their phone.

---

# Section D: paste etiquette

## How to copy from the terminal

- **macOS Terminal:** click into the window, press Command A to select all, then Command C. Or drag over the part you want, then Command C.
- **Windows PowerShell:** drag the mouse over the text, then press Enter, which copies the selection. In Windows Terminal, Ctrl and Shift and C also works. If they are stuck, right click the title bar, then Edit, then Select All, then Edit, then Copy.
- Then paste into the chat as text.

## What you ask for, exactly

Ask for it in these words, or close to them:

> Please paste everything the terminal shows, starting from the line where you typed the command, all the way to the end. Do not tidy it up or shorten it.

Three things people do that break the diagnosis, so head them off:

- **They paste only the last line.** The error is often three lines above the last line, and the typed command is always above that.
- **They redact usernames and file paths.** Those are exactly what you need to see, and they are on their own machine, not being published anywhere. Tell them not to edit the paste.
- **They send a photo of the screen.** Fine for phone screens, not for terminal output, because you cannot read a long path reliably from a photo and you cannot copy it back into a command. Ask for text.

## The one exception, and what to do if it is breached

**Never the 64 digit encryption key.** It is the only thing that should never appear in this chat. Everything else in a terminal paste is fine.

The Android command is built so this cannot normally happen: the key goes into a hidden prompt, so it is not in the visible output and not in their shell history.

If a key does appear in a paste anyway, because they passed it as an argument or used a show key option, do this immediately and without drama:

1. Tell them it is now in the chat and probably in their shell history.
2. Tell them they can issue a new key by turning End-to-end encrypted backup off and back on in WhatsApp, which invalidates the old one.
3. Do not repeat the key back to them, do not quote the line containing it, and do not put it in any summary.

The same bar applies to everything you ask for: counts, sizes, dates, filenames and error text are enough to solve every problem in this file. If a request would pull message content or contact names into the chat, it is the wrong request.
