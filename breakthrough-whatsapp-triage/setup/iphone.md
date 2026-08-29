# iPhone branch
**Before anything else: is the computer a Mac?** If it is, and WhatsApp is or can be signed in on that Mac, stop here and go to `mac-desktop.md`. The Mac app keeps its own readable copy of the history, which reaches the same `export.json` in about two minutes with no cable and no backup, and it does not care which phone the user carries. This branch is for a computer that cannot do that.

End state: a local (not iCloud) device backup on the computer, and the tool pointed straight at that backup folder to produce `export.json`.

Prerequisite: `computer-prep.md` finished, all four handoff facts confirmed. On a Mac that includes the Full Disk Access probe passing. Every `python3` below means whichever word you settled on for this machine.

**Two honesty notes to hold in mind, and to share if the user asks:**

- **iPhone on Windows is the least travelled path here.** Tell the user so before they invest an hour. It should work, and it may need extra rounds.
- The tool takes a backup folder directly: it reaches into the backup, pulls out the WhatsApp files, and wires up the message and contact databases by itself. **The user never has to hunt for or extract individual files.** This was read from the tool's source rather than confirmed on a finished real backup, so treat it as expected behavior with a probe attached (Step I6), not as a promise.

**One caution specific to iPhone.** Do not turn on WhatsApp's own end-to-end encrypted backup for this path. If it is already on and the export later says essential WhatsApp files are missing, that is the first thing to suspect. This is the opposite of the Android branch, so do not carry advice across from it.

## Step I1: pick the backup app

- **macOS Catalina and newer:** Finder does it. No install needed.
- **macOS Mojave and older:** iTunes.
- **Windows:** they need Apple's software. The current one is the **Apple Devices** app from the Microsoft Store. Older machines may have iTunes instead, which is fine. If neither is installed, install Apple Devices from the Microsoft Store now.

**Probe:** ask which of those they have, by name, and whether it opens. Where the backup lands depends on this answer, so do not guess it later.

## Step I2: connect the phone and get through Trust

Plug the phone into the computer with a cable that carries data. Then:

1. Unlock the phone.
2. A prompt appears on the phone: **Trust This Computer?** Tap Trust, then enter the phone passcode.
3. If no prompt appears, unplug and replug with the phone unlocked.

**Probe:** the phone should now show up in the app. In Finder it appears in the left sidebar under Locations. In Apple Devices or iTunes it appears near the top left. Ask them to confirm they can see the phone's name there and read it back. If they cannot, go to `troubleshooting.md`, the row about the phone never appearing.

## Step I3: set it to back up locally, and settle encryption

Click the phone, then the General tab in Finder (Summary in iTunes). In the Backups section:

1. Choose **Back up all of the data on your iPhone to this Mac** (Windows wording: **this computer**). If it is set to iCloud, the computer holds nothing usable and this is the single most common reason a MobileSync folder is empty or years out of date.
2. The **Encrypt local backup** checkbox:
   - **Unencrypted is simpler.** If it is off, leave it off and go to Step I4.
   - If it is on and they can turn it off, that is the easier path. iOS asks for the existing password to turn it off.
   - If they cannot turn it off, because they do not know the password or a work device policy enforces it, that is fine, do not fight it. Keep it on and add the decryption support in Step I7.

Do not let them set a new encryption password just for this. Turning encryption on when it was off adds a password to remember and buys nothing here.

**Probe:** ask them to read back both settings, the backup destination and whether the encrypt checkbox is ticked. Record the answer. It determines which command you give in Step I6.

## Step I4: run the backup, and set the clock expectation

Click **Back Up Now**. Then tell them, before they walk away:

> This is the long part. It is often several gigabytes and takes anywhere from 10 to 60 minutes on the first run. The progress bar can look stuck for long stretches. Leave the phone plugged in and unlocked, do not unplug it, and do not close the window.

**Probe:** when it finishes, the same screen shows a line like "Last backup to this Mac: today at 3:42 PM". Ask them to read that line back. Do not proceed on "I think it is done", and do not start the export while a backup is still running, a half written backup produces confusing errors.

## Step I5: find the backup folder and prove it is real

The folder is named as a long string of letters and numbers. There may be several if they have backed up more than one device.

**macOS:**

```
ls -lt ~/Library/Application\ Support/MobileSync/Backup/
```

**Windows,** run both, one of them will have it:

```
dir "$env:USERPROFILE\Apple\MobileSync\Backup"
dir "$env:APPDATA\Apple Computer\MobileSync\Backup"
```

The first Windows location is used by the Apple Devices app and the Microsoft Store version of iTunes. The second is used by the older desktop iTunes. Which one exists depends on the answer from Step I1.

**Good output** lists at least one long folder name with today's date. Take the newest one. Ask them to paste the whole listing so you can read the dates yourself rather than asking them to judge.

**Now the probe that matters most.** Have them list what is inside that folder:

macOS:

```
ls -lh ~/Library/Application\ Support/MobileSync/Backup/<the-folder-name>/ | head
```

Windows:

```
dir "<full path to the folder>"
```

**Good output contains** a file named `Manifest.db` with a real size (megabytes, not zero), a `Info.plist`, a `Status.plist`, and many two character folders such as `00`, `01`, `fe`.

| What came back | Conclusion |
|---|---|
| `Manifest.db` with real size, plus two character folders | correct folder, continue to Step I6 |
| no `Manifest.db` at all | wrong folder, go back and take a different one from the listing |
| a `Manifest.db` of exactly 0 bytes | this is almost always a folder the tool touched earlier by mistake, see the note below |
| `Operation not permitted` on macOS | Full Disk Access, return to `computer-prep.md` Step 7 |
| folder is empty or dated months ago | the phone is backing up to iCloud, return to Step I3 |

**The 0 byte `Manifest.db` trap, verified this session.** If the tool is ever pointed at a folder that is not a backup, it creates an empty `Manifest.db` there as a side effect, then reports the backup as encrypted, which sends the whole diagnosis down the wrong road. If you see a 0 byte `Manifest.db`, that folder is not a backup. Delete that empty file, and find the right folder. Checking this before running is much cheaper than untangling it afterwards.

## Step I6: export

Use the full path to the backup folder, in quotes. Paths here contain spaces, and unquoted paths fail in ways that look like missing files.

**Unencrypted backup:**

```
python3 -m Whatsapp_Chat_Exporter -i -b "/full/path/to/Backup/<the-folder-name>" -j export.json --no-html
```

**WhatsApp Business app instead of regular WhatsApp:** add `--business` to that command.

**Good output contains,** in order:

```
Extracting WhatsApp files
Extracted <a number> WhatsApp files in <some time>
JSON file saved...(some size)
Everything is done!
```

That first pair of lines is the confirmation that the tool found and unpacked the WhatsApp data out of the backup on its own. If you see them, the expected behavior held on this machine.

One line to watch for in passing: `Contact database not found. Skipping...`. The run still succeeds, but no `ContactsV2.sqlite` lands in the working folder, so some chats will later show as unresolved and get a copy button instead of a reply link. Note it now and leave `contacts_db` out of the config in Step I8 if the file really is not there.

Ask for the full paste, including the typed command. If the run mentions a password, or dependencies for encrypted backup, go to Step I7. If it says essential WhatsApp files are missing, go to `troubleshooting.md`.

**Confirming probe.** Do not open the export to check it, and do not write a one liner that reads it. It is tens of megabytes and it must never enter your context. The doctor already reports what you need:

```
python3 wa_doctor.py
```

Good output, in the `[export]` block: `parses : yes`, a `chats` count and a `messages` count both above zero, and a `newest` date of today.

**Expect one false alarm on this branch.** The doctor's `[db]` block only opens files whose names end in `.sqlite` or `.db`. On the iPhone path the message database is extracted under a long hash filename with no extension, so `[db]` can report that it found nothing even on a perfectly healthy run. Judge this branch by the `[export]` block, not by `[db]`.

Read the message count back and ask whether it sounds roughly right. A number far below expectation is usually the ceiling from `00-overview.md`, not a failure, but check the row in `troubleshooting.md` before concluding.

## Step I7: encrypted backups only

Symptom that sends you here: the run prints `Encryption detected on the backup!`, or complains it does not have the dependencies to handle an encrypted backup.

Install the decryption support:

```
python3 -m pip install git+https://github.com/KnugiHK/iphone_backup_decrypt
```

This one comes from a source repository rather than the package index, so it may need Git installed on Windows. If it fails for that reason, the honest options are to install Git, or to turn off backup encryption in Step I3 and make a fresh backup.

**Probe:** rerun the exact Step I6 command. The tool now prints `Encryption detected on the backup!` and then asks:

```
Enter the password for the backup:
```

Tell them beforehand: **nothing appears on screen while typing the password, that is deliberate.** This is the iPhone backup password they set in iTunes or Finder, not their Apple ID password and not the phone passcode. Getting those confused is common.

Wrong password gives `Failed to decrypt backup: incorrect password?`. Decryption also takes noticeably longer than the unencrypted path, so set that expectation before they start.

## Step I8: write the config file, which is what marks setup as done

The skill routes on a `config.json` in the working folder, so setup is not finished until that file exists and says so. Write it yourself, in the working folder next to `export.json`. Do not make the user type JSON.

```json
{
  "platform": "ios",
  "setup_complete": true,
  "export_path": "export.json",
  "contacts_db": "ContactsV2.sqlite",
  "days": 3,
  "link_style": "app",
  "ignored_jids": []
}
```

- `contacts_db` matters on this branch. The export run extracts `ContactsV2.sqlite` into the working folder, and the digest reads it to turn `@lid` style chats into real phone numbers, which is what lets those rows carry a reply link instead of a copy button. If the file is absent the digest still builds, it just marks those chats unresolved, so check the working folder for that filename before naming it here.
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

Give the user this short version once setup succeeds, since this is the part they repeat.

1. Plug the phone in, unlock it, open Finder (or Apple Devices or iTunes).
2. Click the phone, then **Back Up Now**. Later backups are incremental, so they are usually much faster than the first one.
3. Wait for the "Last backup" line to show today.
4. In the terminal, in the working folder, rerun the same command:

```
cd ~/Documents/WhatsApp-Triage
python3 -m Whatsapp_Chat_Exporter -i -b "/full/path/to/Backup/<the-folder-name>" -j export.json --no-html
```

(On Windows, `cd "$env:USERPROFILE\Documents\WhatsApp-Triage"`, their Python word, and their own backup path.)

The backup folder name does not change for the same phone, so save that exact command for them once it works. It is the whole refresh. If they get a new phone, the folder name changes and they will need Step I5 again.

Do not tell them to delete the old backup to save space until the JSON has been confirmed good, and even then leave that decision to them.
