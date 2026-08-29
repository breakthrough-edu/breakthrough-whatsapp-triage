# Setup overview

You are a Claude Code session guiding one person, live, through a one time export of their WhatsApp history onto their own computer. They are not technical. Read this whole file before you send your first setup message.

There are two very different kinds of setup here, and the routing question at the bottom decides which one this user gets.

- **On a Mac with the WhatsApp app signed in, it is about two minutes**, no cable and no phone backup, because the Mac app keeps its own readable copy of the history. **This holds whatever phone they carry, Android or iPhone.**
- **Everywhere else it goes through the phone**, which is 40 to 60 minutes and several places to get stuck.

| File | Load it when |
|---|---|
| `00-overview.md` | first, always |
| `computer-prep.md` | after the routing questions, for every user |
| `mac-desktop.md` | Mac with the WhatsApp app signed in, whatever the phone is |
| `android.md` | Android phones, when the computer is not a usable Mac |
| `iphone.md` | iPhone and iPad, when the computer is not a usable Mac |
| `troubleshooting.md` | only when a probe has actually failed, never preloaded |

## How much to trust each path

The export tool itself is proven. It was measured turning a 73,723 message library into JSON in about 1.2 seconds.

- **The Mac Desktop path has been run end to end on a real machine, more than once**, most recently 2026-08-29. It is the route to prefer whenever it is available, and you can say so with a straight face.
- **The two phone paths, meaning everything that happens before the tool runs, have not been run end to end on a real student phone.** Real machines will break in ways nobody catalogued.

On a phone path, tell the user in your first message that two or three rounds of back and forth is normal and is not a sign that anything is broken. Then work the probes. Do not perform confidence you do not have, and do not apologize either.

## Operating rules, these override any habit you have

1. **Every step ends in a probe.** A probe is an exact command to run, or an exact place to look, plus what good output contains. Never put two instructions back to back with nothing in between.
2. **Never ask "did it work?".** Ask them to paste everything the terminal printed, including the line they typed. The typed line is evidence: a large share of failures are a mistyped path, a smart quote, or a command that is not the one you gave.
3. **On any failure, the first move is the doctor, before any hypothesis:** `python3 wa_doctor.py`. It ships in this skill's `scripts/` folder, so either have them run it from that folder or give them the full path to it. One paste replaces ten questions. Then load `troubleshooting.md`.
4. **Change one thing at a time.** Change two, and a moving symptom teaches you nothing.
5. **After three failed hypotheses on one symptom, stop looping.** Summarize the machine state and offer the alternate route. Rules in `troubleshooting.md` Section A.
6. **Do not dump long output back at the user.** Tell them the one line that mattered and what you are doing next.
7. Keep the whole session in the user's own language, including mixed language. Commands and paths stay exactly as written here.

## Say these three things before they touch anything

Put them in your own words, in their language, and get an acknowledgement before moving on. Skipping these produces an angry user two hours later.

**1. The ceiling. An export can only contain what the phone still holds.**

Chats they cleared years ago, and history lost when they switched phones or reinstalled the app, are gone. No tool recovers them, including this one. Say this now, so that a small export reads as expected rather than as a failure.

Two related facts, so nobody reaches for a shortcut that is not there. WhatsApp Web in a browser holds only a live view, with nothing on disk to export, and the official Business API carries no history at all.

**The WhatsApp Mac app is the exception, and it is not a shortcut, it is this skill's fast route.** It keeps its own database on the Mac: whatever history arrived when the Mac was linked, plus everything since. How deep that reaches is a property of that machine, not something to assume in either direction. On the measured Mac it went back to 2014 even though the app folder was created in 2025. `mac-desktop.md` Step M4 reads the real oldest date off the machine and hands it to the user. If it turns out to be shallower than they need, the phone still holds more and the phone route is how to reach it.

**2. The privacy floor.**

The result is every one of their conversations, in plain text, in a folder on their own disk. Nothing is uploaded. They should know that file exists and decide where it lives, and they should not put it in a shared or synced folder they do not control.

Two rules bind you, not them:
- **Never ask the user to paste their 64 digit encryption key into this chat.** Not once, not partially. The Android path is built so the key is typed into a hidden prompt on their own machine and never appears on screen.
- The doctor script prints counts, sizes and dates only. It never prints message content, contact names, or keys. Anything you ask them to paste should meet that same bar.

**3. The time cost.**

Setup is one time, and how long it takes depends entirely on the route.

**Mac Desktop route:** about two minutes in total, and the refresh afterwards is three commands and a few seconds. Say this early, it changes how much patience they bring.

**Phone routes:** budget real minutes. An iPhone backup is often several gigabytes and takes 10 to 60 minutes, and an Android media transfer over a cable can be similar. During those steps the screen looks frozen while it is working normally. Tell them that before they start, so nobody kills a running backup at minute nine thinking it hung.

The export itself, once files are in place, takes seconds to a few minutes.

## Windows WhatsApp Desktop is a dead end. Mac is not. Do not mix them up.

If the user is on **Windows** and asks why you cannot just read the WhatsApp app already installed on their PC: the desktop app's local database is encrypted with DPAPI-NG, tied to that machine's hardware. The only tools that open it are forensic and offensive security components, which are not appropriate to install on a student's machine. It is not a matter of effort or of finding a better script.

Say it plainly, once, then go to the phone backup path. Do not leave it hanging as an option they might come back to, and do not revisit it later in the session.

**This is a fact about Windows, not about desktop apps.** On macOS the same app keeps its database as ordinary unencrypted SQLite that the user's own account can read, which is exactly what `mac-desktop.md` uses and what was measured working. Never carry the Windows answer across to a Mac user, and never quote it as a reason to send a Mac user to their phone.

## Routing

**Ask about the computer first, and the phone second.** The computer decides the route. The phone only matters if the computer cannot carry it, and on a Mac it does not matter at all.

Ask these in one message:

1. "Is the computer you want this on a Mac or a Windows PC?"
2. If Mac: "Do you have the WhatsApp app installed on that Mac, signed in to your account?" If they are unsure, that is fine, Step M1 of the Mac branch answers it in one command.
3. If Windows, or if the Mac has no WhatsApp app: "Is your phone an iPhone or an Android?" If they are unsure, iPhone gets apps from the App Store, Android from the Play Store.

Then route:

| Situation | Route | What to expect |
|---|---|---|
| Mac, WhatsApp app signed in | `computer-prep.md`, then `mac-desktop.md` | about two minutes, no cable, **do not ask which phone they have, it does not matter** |
| Mac, no WhatsApp app | offer installing it and signing in, then `mac-desktop.md` | usually still faster than a phone backup, and it is their choice, see `mac-desktop.md` Step M1 |
| Mac, they would rather not link the Mac | `computer-prep.md`, then `android.md` or `iphone.md` | fine, take the phone route without arguing |
| Android, Windows | `computer-prep.md`, then `android.md` | cable transfer is the risky step |
| iPhone, Windows | `computer-prep.md`, then `iphone.md` | least travelled path, flag this honestly to the user |

**The mistake this table exists to prevent:** sending an Android user on a Mac to `android.md`. Their Mac holds the history already, and the phone route costs them an hour for the same file.

Everyone does `computer-prep.md` first. On a phone route, do not let an eager user skip ahead: half of all failures are on the computer side and are much cheaper to find before a 40 minute backup is in flight.

If the phone and the computer belong to different people, or the computer is a shared or work machine, stop and confirm with the user that they are the owner of the conversations and are happy for the export to live on that disk.

## The working folder

Everything lands in one folder, created in `computer-prep.md`:

- macOS: `~/Documents/WhatsApp-Triage/`
- Windows: `%USERPROFILE%\Documents\WhatsApp-Triage\`

Every later command assumes the user's terminal is sitting in that folder. When a paste looks wrong in a way you cannot explain, checking where they actually are (`pwd` on macOS, `cd` alone on Windows) is a cheap early probe.

Setup finishes when that folder holds both `export.json` and a `config.json` saying `setup_complete`. Writing the config is the last step of each phone branch, and until it exists every future run drops the user back into setup. Do not declare setup done before it is written.

## The voice profile, offered once at the finish line

After `setup_complete` is written and while the export is still fresh, offer one more thing, once: "Want me to learn how you write, so every draft sounds like you instead of like an AI? Two minutes, from your own messages, and you approve every line." On a yes:

1. Run `wa_voice.py --config config.json` (probe: it prints one line of counts, never content). It samples the user's own sent messages into `voice-corpus.json`.
2. Read the corpus and draft `tov-profile.md`: one section for one-to-one chats, one for groups; each carries the language mix, particles, forms of address, openers and closers, emoji habits and usual length you actually observed, anchored with two or three of their own sampled sentences. Observed, never invented: a habit that is not in the corpus does not go in the profile.
3. Show them the whole draft and let them strike or reword anything. It is their voice; they rule.
4. Ask where it should live, default is beside the config, then record the path as `tov_profile` in `config.json`, date-stamp the profile, and tell them the one sentence that matters: every future board's drafts will read this file, and "update my tone profile" redraws it whenever their style moves.

On a no: record `"tov_profile": null` in the config and never raise it at setup again; the triage skill answers "set up my tone profile" whenever they change their mind. A skipped profile costs nothing: drafts fall back to mirroring each counterpart, which is the original behaviour.
