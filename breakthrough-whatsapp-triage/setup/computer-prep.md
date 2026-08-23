# Computer prep

Everyone does this before touching the phone. End state: a terminal the user can work in, Python 3.10 or newer, the export tool pinned at 0.13.0 with crypto support, one working folder, and (on Mac, for iPhone users) Full Disk Access granted.

Do not skip ahead to the phone branch. Failures here are cheap to find. The same failure discovered after a 40 minute backup is expensive and demoralizing.

## The command translation, settle it once

Every command in these files is written with `python3`. That is correct on macOS. On Windows the same thing is usually spelled `py -3`, sometimes `python`, and often `python3` does not exist at all.

Step 2 below decides which of the three works on this machine. **Write the answer down in your working context and use it for the rest of the session.** When you hand the user a command from any later file, translate `python3` to their word before you send it. Getting this wrong produces the single most common Windows failure.

Note also: `python3 -m Whatsapp_Chat_Exporter` is used everywhere instead of the short `wtsexporter` command. Both exist (0.13.0 installs `wtsexporter`, `waexporter` and `whatsapp-chat-exporter`), but the short commands only work if the install folder is on PATH, which on Windows it frequently is not. The `-m` form works either way. Only mention the short alias if the user asks.

## Step 1: open a terminal

- **Windows:** press the Start button, type `powershell`, open Windows PowerShell. (Terminal or PowerShell 7 are both fine if that is what opens.)
- **macOS:** press Command and Space, type `terminal`, press Return.

**Probe.** Ask them to paste the first line or two the window shows, exactly as it appears. You are confirming a terminal is open and reading which shell it is. If they send a screenshot instead, that is fine, but from here on ask for text: you need to be able to read exact paths.

## Step 2: find their Python

Ask them to run these, one line at a time, and paste everything including the lines they typed.

Windows:

```
py -3 --version
python --version
```

macOS:

```
python3 --version
```

**Good output contains** the word `Python` and a version number of `3.10` or higher, for example `Python 3.12.4`.

**How to read it:**

| What came back | Conclusion |
|---|---|
| `Python 3.10` or newer | done, record that command as their Python word, go to Step 4 |
| `Python 3.9` or older | too old, the tool requires 3.10 or newer, install a current Python in Step 3 |
| `Python was not found` or the Microsoft Store opens | not installed, or the Store alias is shadowing it, go to Step 3 |
| `command not found` (macOS) | Xcode command line tools missing, see Step 3 |
| nothing at all, or the prompt just returns | ask them to paste the whole window, something else is wrong |

If both `py -3` and `python` work on Windows, prefer `py -3`. The `py` launcher is installed into the Windows folder itself, so it keeps working even when "Add Python to PATH" was never ticked.

## Step 3: install Python (only if Step 2 failed)

**Windows.** Send them to python.org, Downloads, the big button for the latest Windows release. Then, on the very first installer screen, before anything else:

> Tick the checkbox at the bottom that says **Add python.exe to PATH**, then click Install Now.

That checkbox is the single most common cause of a broken setup, because the installer leaves it unticked by default and the consequence only appears later as `'python' is not recognized`. Call it out explicitly and ask them to confirm they ticked it before they click.

If they already clicked past it, do not make them uninstall. `py -3` almost always works anyway. Rerun the Step 2 probe and take whichever command answers.

**macOS.** Modern macOS has `python3`, but running it the first time may pop a dialog asking to install the command line developer tools. Tell them to accept and wait for it to finish, then rerun the Step 2 probe. If macOS is older and gives `Python 3.9`, install a current version from python.org the same way as above.

**Probe after installing:** they must close the terminal window completely and open a new one, then rerun Step 2. A terminal opened before the install cannot see the new Python. Ask for the fresh paste including the typed line. Do not accept "I installed it" as evidence.

## Step 4: make the working folder and go there

Everything lives in one folder so paths stay short and you always know where they are.

Windows:

```
mkdir "$env:USERPROFILE\Documents\WhatsApp-Triage"
cd "$env:USERPROFILE\Documents\WhatsApp-Triage"
pwd
```

macOS:

```
mkdir -p ~/Documents/WhatsApp-Triage
cd ~/Documents/WhatsApp-Triage
pwd
```

**Good output** is the last line showing a path that ends in `WhatsApp-Triage`.

If `mkdir` complains that the folder already exists, that is fine, the `cd` still matters. If `pwd` shows anything else, they are not where you think they are and every later command will fail confusingly. Fix it now.

**Say this once:** for the rest of setup, every command must be typed in this same window. If they close it, they must `cd` back here before continuing.

## Step 5: install the export tool

One command for everyone, both phone types, both operating systems. It pins the version and pulls the crypto support that Android needs. Installing the extra on an iPhone machine is harmless, so do not branch here.

```
python3 -m pip install "whatsapp-chat-exporter[crypt15]==0.13.0"
```

Two things about that line, both deliberate:
- `python3 -m pip` rather than a bare `pip`. On a machine with more than one Python, a bare `pip` can install into a different Python than the one that will run the tool, which produces the maddening "pip says it is installed but it cannot be found" symptom. The `-m` form installs into the interpreter you just verified.
- `==0.13.0` is a hard pin. Later versions may change the shape of the exported JSON, which breaks the rest of this skill. Do not let a user "just upgrade it".

**Probe.**

```
python3 -m pip show whatsapp-chat-exporter
```

**Good output contains** `Version: 0.13.0` and a `Location:` line. Read the `Location:` path, it tells you which Python received the install, which is the fact you need if Step 6 fails.

Expect a lot of scrolling output from the install itself, and possibly a yellow notice about a new version of pip. That notice is not an error. Tell them to ignore it.

## Step 6: prove the tool actually runs

Installation is not the same as working. This is the probe that proves the package imports and the command form is right.

```
python3 -m Whatsapp_Chat_Exporter --help
```

**Good output** is a long usage listing whose last lines contain:

```
WhatsApp Chat Exporter: 0.13.0
```

Ask for the last three lines only, they are enough and they carry the version.

| What came back | Conclusion |
|---|---|
| usage text ending in `0.13.0` | prep is working, continue |
| `No module named Whatsapp_Chat_Exporter` | pip installed into a different Python than this command uses, this is the two Pythons problem, go to `troubleshooting.md` |
| `No module named pip` | the Python they found has no pip, go to `troubleshooting.md` |
| a version that is not 0.13.0 | an older install is shadowing it, reinstall with the pinned command in Step 5 |

Note the capital letters and the underscores in `Whatsapp_Chat_Exporter`. It is spelled exactly that way, and a lowercase or hyphenated version will fail. If a paste shows a slightly different spelling in the typed line, that is your answer, no further diagnosis needed.

## Step 7: macOS Full Disk Access (iPhone users on a Mac only)

Skip this entirely for Android, and for iPhone users on Windows.

An iPhone backup lives in a folder that macOS protects. A terminal cannot read it until the user grants Full Disk Access, and this was reproduced directly: without it, reading that folder returns `Operation not permitted` and the export tool exits with a permission error.

**Probe first, do not grant blindly:**

```
ls ~/Library/Application\ Support/MobileSync/Backup/
```

| What came back | Conclusion |
|---|---|
| `Operation not permitted` | Full Disk Access is missing, do the grant below |
| a long folder name of letters and numbers, or several | access is fine and a backup already exists, go to `iphone.md` |
| `No such file or directory` | access may be fine but no local backup has ever been made, go to `iphone.md` and make one |
| an empty result with no error | access is fine, no backups yet, go to `iphone.md` |

**The grant, if needed.** Walk them through it one line at a time and confirm each:

1. Open System Settings, then Privacy and Security, then Full Disk Access.
2. Find their terminal app in the list (Terminal, or iTerm, or whichever they opened in Step 1). If it is not listed, use the plus button and add it from the Applications Utilities folder.
3. Turn its switch on. macOS may ask for the login password, which is normal and is theirs alone to type.
4. **Quit the terminal app completely and open it again.** Not just the window: quit the application (Command Q, or right click the Dock icon and Quit). This is the step people skip, and skipping it means the permission does not take effect and everything looks unchanged.
5. Open a new terminal, `cd` back to the working folder, and rerun the probe above.

If the probe still says `Operation not permitted` after a genuine quit and reopen, go to `troubleshooting.md` rather than granting more permissions. Adding more toggles blindly is how a machine ends up in a state nobody can reason about.

## Step 8: baseline the doctor while nothing is broken yet

Run the doctor once now, before the phone is involved. It costs one command and pays twice: you learn this machine's exact state, and the user has already run the thing you will ask for first the moment something breaks.

```
python3 wa_doctor.py
```

Run it from this skill's `scripts/` folder, or give the full path to it. Ask for the whole report. Its own header says it is safe to paste, since it carries no message text, no contact names and no passwords.

**Expected at this point, and not a fault:**

- `[os]`, `[python]`, `[pip]` and `[package]` all healthy, with `[package]` showing 0.13.0
- `[workdir]` reporting `config : not found`
- `[candidates]`, `[db]` and `[export]` finding nothing yet
- `[verdict]` reading `SETUP INCOMPLETE AT config file`

That verdict is the correct state before any phone backup exists. The config file is written at the end of the phone branch. What matters here is that every block above `[workdir]` is clean.

If `[package]` is not clean, fix it now. Going to the phone with a broken tool means discovering it after a 40 minute backup.

Reading the report in detail is Section B of `troubleshooting.md`, but do not load that file unless something is actually wrong.

## Step 9: hand off

Before leaving this file, you should be able to state all five:

1. their Python word (`python3`, `py -3`, or `python`),
2. `Version: 0.13.0` seen in a paste,
3. the working folder path from `pwd`,
4. a doctor report whose only failure is `config file`,
5. for iPhone on Mac, the MobileSync folder listed without a permission error.

If any of those is missing, you are not done here, whatever the user says.

Then load `android.md` or `iphone.md`. Tell the user what happens next and roughly how long it takes, so the phone step does not arrive as a surprise.
