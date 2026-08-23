# Android branch

End state: `msgstore.db.crypt15` sitting in the working folder, decrypted by the tool using a key the user types into a hidden prompt, exported to `export.json`.

Prerequisite: `computer-prep.md` finished, all four handoff facts confirmed. Every `python3` below means whichever word you settled on for this machine.

Warn the user before starting: this branch has not been run end to end on a real student phone. It is built from verified tool behavior, and the phone side may need a round or two of adjusting. That is expected.

## Step A1: turn on the encrypted backup, with a key not a password

This is the only step where a wrong tap costs the whole path, so go slowly and confirm each screen.

On the phone, in WhatsApp:

1. Settings, then Chats, then Chat backup.
2. Open **End-to-end encrypted backup**.
3. Turn it on. WhatsApp offers two ways to protect it: a password, or a 64 digit key.
4. Choose **Use 64-digit encryption key instead**. Not the password option.
5. WhatsApp shows the 64 character key and asks them to save it. They must write it down or screenshot it and keep it somewhere they can copy from later.

**Say this now, plainly:** never send that key to you, to this chat, or to anyone. Later they will type it directly into their own computer at a prompt that hides what is typed. You will never see it and you will never ask for it.

If they already had encrypted backup on with a **password**, they can switch to a key: same screen, turn it off, turn it back on, choose the key option. Some phones require re-entering the password to change it. If they cannot get past that screen, note it and go to `troubleshooting.md` rather than guessing.

**Probe.** Ask what the End-to-end encrypted backup screen says now. Good answer: it shows the feature as on, and the words "64-digit encryption key". If it says password, they took the wrong branch and the export will fail later with a decryption error, so fix it here.

## Step A2: make a fresh local backup

Still in Settings, Chats, Chat backup, tap **Back up**. Tell them to leave the phone alone, screen on, until it finishes. On a large library this can take many minutes and the progress can appear stuck.

**Probe:** the Chat backup screen shows a "Last backup" time of today, within the last few minutes. Ask them to read that line back to you. Do not proceed on "I think it finished".

Note: Google Drive backup and this local database file are different things. The user does not need Google Drive on for this. What matters is the local file created in the next step's folder.

## Step A3: find the database file on the phone

Open the phone's **Files** app, then Internal storage.

Look in this order:

1. `Android/media/com.whatsapp/WhatsApp/Databases/` (newer Android and newer WhatsApp, this is the usual place now)
2. `WhatsApp/Databases/` (older layout, at the top level of internal storage)

The `Android/media/` folder is browsable on modern Android. `Android/data/` is blocked, so if they wander into that one and hit a wall, redirect them.

**Probe.** Ask them to read out the exact filenames in the Databases folder, and the size and date of the biggest one. Good output includes a file named exactly `msgstore.db.crypt15` with today's date. Files named `msgstore-2026-08-21.1.db.crypt15` are older dated copies, ignore those and take the plain one.

| What they report | Conclusion |
|---|---|
| `msgstore.db.crypt15`, dated today | correct, continue |
| `msgstore.db.crypt14` or `.crypt12` | the encrypted backup did not take effect, redo A1 and A2 |
| no Databases folder in either place | go to `troubleshooting.md`, do not go hunting at random |
| only dated files, no plain `msgstore.db.crypt15` | take the newest dated file, and keep its full name exactly |

If they also see `wa.db.crypt15` in that folder, note it. It holds contact names and it is optional, covered in Step A7.

## Step A4: connect the phone to the computer

Plug the phone in with a USB cable that carries data. Many charging cables do not. If nothing appears, a different cable is the cheapest first thing to try.

On the phone, a notification appears about the USB connection. Tap it and choose **File transfer** (sometimes called MTP or Transferring files). Charging only mode shows nothing on the computer, and this is the most common stall on this step.

- **Windows:** the phone appears in File Explorer under This PC.
- **macOS:** macOS cannot browse Android storage on its own. They need a helper app (OpenMTP is a common free one). If installing one is not acceptable, use the alternate route below.

**Probe:** ask them to confirm they can see Internal storage and navigate to the Databases folder from the computer, and to read back one filename they see there. Seeing the phone's name alone is not enough, folders often stay locked until File transfer mode is selected.

**Alternate route if the cable path will not work at all:** the `.crypt15` file is encrypted and is not readable without the key, so moving it through the user's own cloud drive or a USB stick is a reasonable fallback. Upload the file from the phone, download it on the computer. The one hard rule: the key never travels with the file, and the key never goes into cloud storage or into this chat.

## Step A5: copy the file into the working folder

Copy (do not move, leave the phone's copy alone) `msgstore.db.crypt15` from the phone into the working folder made in prep.

**Probe.** In the terminal, in the working folder:

Windows:

```
dir
```

macOS:

```
ls -lh
```

**Good output** lists `msgstore.db.crypt15` with a size in the tens or hundreds of megabytes. A size of 0, or a few kilobytes, means the copy failed or was interrupted, and the export will fail with a confusing format error later. Recopy now.

If the filename lost its `.crypt15` ending during the copy, rename it back. The tool reads the crypt version out of the filename, and a renamed file produces `Unknown backup format`.

## Step A6: export, JSON first

Media comes later, on purpose. This first run proves the decryption and the pipeline with the fewest moving parts.

```
python3 -m Whatsapp_Chat_Exporter -a -b msgstore.db.crypt15 -k -j export.json --no-html
```

The bare `-k` at the end is deliberate: with no value after it, the tool stops and asks for the key itself.

**Tell them before they run it:**

> It will print a line asking for your encryption key. Type or paste your 64 digit key and press Enter. **Nothing will appear on the screen while you type. That is normal and correct, the key is hidden on purpose.** Spaces in the key are fine.

That warning matters. Without it, users type the key, see nothing, assume the keyboard is broken, and retype it several times into the same prompt.

**Good output contains,** in order:

```
Enter your encryption key:
Decryption key specified, decrypting WhatsApp backup...
JSON file saved...(some size)
Everything is done!
```

Ask them to paste everything, including the command line they typed. If any of those three lines is missing, you have the symptom you need for `troubleshooting.md`.

**Confirming probe.** Do not open the export to check it, and do not write a one liner that reads it. It is tens of megabytes and it must never enter your context. The doctor already reports what you need:

```
python3 wa_doctor.py
```

Good output, in the `[export]` block: `parses : yes`, a `chats` count and a `messages` count both above zero, and a `newest` date of today. The `[db]` block additionally opens the decrypted `msgstore.db` that the run left in the working folder and prints the date range of messages inside it, which is the honest answer to "how far back does my history actually go".

Read the message count and that date range back to the user and ask whether it sounds roughly right. If it is far smaller than expected, that is usually the ceiling from `00-overview.md` rather than a bug, but check the row in `troubleshooting.md` before concluding either way.

**One privacy point to mention here.** The run leaves a decrypted `msgstore.db` next to `export.json`. That file, and the export itself, are readable by anything that can read that folder. Nothing left the machine, and nothing was uploaded, but the user should know both files exist and should not put that folder in a shared drive.

## Step A7: media and contact names (optional, do it after the JSON works)

Only offer these once Step A6 has succeeded. Each one is a separate change, run separately.

**Contact names.** If `wa.db.crypt15` was in the Databases folder, copy it into the working folder too and rerun with it added:

```
python3 -m Whatsapp_Chat_Exporter -a -b msgstore.db.crypt15 --wab wa.db.crypt15 -k -j export.json --no-html
```

Without it, some chats appear as phone numbers instead of names. It prompts for the same key.

**Media.** On the phone, the media lives beside the Databases folder in `.../com.whatsapp/WhatsApp/Media/`. Copy the whole `WhatsApp` folder (the one containing `Media`) into the working folder, keeping that name, then rerun the same command as Step A6 without `--no-html`.

Warn them first: this transfer can be many gigabytes and take a long time over a cable, and during the export a line saying `Copying media directory...` can sit there for many minutes while it duplicates the files into the output folder. **That is work, not a hang.** If disk space is tight, add `-c`, which moves the media instead of copying it.

Media is optional for triage. If the transfer is painful, skip it, the text export stands on its own.

## Step A8: write the config file, which is what marks setup as done

The skill routes on a `config.json` in the working folder, so setup is not finished until that file exists and says so. Write it yourself, in the working folder next to `export.json`. Do not make the user type JSON.

```json
{
  "platform": "android",
  "setup_complete": true,
  "export_path": "export.json",
  "days": 3,
  "link_style": "app",
  "ignored_jids": []
}
```

- Do not set `contacts_db` on this branch. Despite the name, the digest reads an iPhone contacts schema through that key, so pointing it at Android's `wa.db` only produces a warning. The Android way to get names is `--wab` in Step A7, which writes them into the export itself.
- `export_path` may be written relative to the config file, which keeps the whole folder portable.
- `link_style` is `app` on a machine with the WhatsApp desktop app installed, `web` on one without it. Ask which they have rather than guessing: guessing wrong shows up much later as reply buttons that do nothing when clicked.
- `days` is the default triage window. 3 is the built in default and it is deliberately narrow, so the first board reads about 60 conversations rather than about 140. The user can widen it any time by asking, and the skill offers that after every board.
- The digest reads only the keys it knows and ignores the rest, so extra keys are harmless but do not invent ones you have not seen.

**Probe:**

```
python3 wa_doctor.py
```

Good output: the `[workdir]` block names the config file instead of reporting `not found`, and the `[verdict]` block no longer says `SETUP INCOMPLETE`. That verdict line is the single check that setup is genuinely finished. Until then, every future run will drop the user back into setup.

## Refresh ritual

This is the part the user actually repeats, so give it to them as a short standalone note once setup succeeds. Every step above was one time except these:

1. On the phone: WhatsApp, Settings, Chats, Chat backup, **Back up**. Wait for "Last backup" to show now.
2. Plug in the cable, choose **File transfer** on the phone.
3. Copy `msgstore.db.crypt15` from `Android/media/com.whatsapp/WhatsApp/Databases/` into the working folder, replacing the old one.
4. In the terminal, in the working folder, run the same export command and type the same 64 digit key at the hidden prompt.

```
cd ~/Documents/WhatsApp-Triage
python3 -m Whatsapp_Chat_Exporter -a -b msgstore.db.crypt15 -k -j export.json --no-html
```

(On Windows, `cd "$env:USERPROFILE\Documents\WhatsApp-Triage"` and their Python word.)

The key does not change unless they turn encrypted backup off and on again. Tell them to keep it where they saved it, because losing it means redoing Step A1 and losing access to older backup files.

Typical refresh time once they have done it once: a few minutes, most of it the phone backup.
