# Reply links

Load this when a link misbehaves, when the user asks why a row copies instead of opening, or when you are about to explain the difference to someone who finds it unfair.

You never build a link yourself. `wa_digest.py` computes `phone`, `resolution`, `reply_mode` and `href_prefix` per chat, and you copy `href_prefix` verbatim. This file explains what it computed and why, so you can answer for it.

## The two formats

```
whatsapp://send?phone=60123456789&text=<urlencoded draft>
https://wa.me/60123456789?text=<urlencoded draft>
```

Both open a one-to-one chat with the message sitting in the compose box, unsent. Neither sends anything. The user still presses send.

`config.json` picks between them with `link_style`:

| `link_style` | Produces | Right when |
|---|---|---|
| `app` (default) | `whatsapp://send?phone=...&text=` | WhatsApp Desktop is installed. Opens the app directly, no browser tab, no extra click |
| `web` | `https://wa.me/...?text=` | The escape hatch. No WhatsApp Desktop, or the browser refuses custom schemes. Opens a wa.me page first, then hands off to WhatsApp Web or the app |

Symptom that the choice is wrong: clicking the button does nothing at all, or the browser says no application is configured for the link. Switch `link_style` to `web` and rebuild the board. `https://api.whatsapp.com/send?phone=...&text=` is the older spelling of the same wa.me behaviour and needs no separate support.

## How the text rides along

`href_prefix` must end in `text=`. The template does exactly this, at the moment the button is pressed:

```js
window.location.href = btn.dataset.href + encodeURIComponent(text);
```

Consequences worth knowing:

- `text=` has to be the **last** parameter, because the encoded draft is glued straight onto the end.
- The URL is built at click time, from the textarea, so it always carries whatever the user just edited.
- `encodeURIComponent` turns newlines into `%0A`, which WhatsApp honours as line breaks. Emoji survive. An `&` or a `#` inside the draft is encoded and cannot break the query.
- Very long drafts can hit a browser URL length limit. Another reason drafts stay short.

## Phone normalization

Digits only. No `+`, no spaces, no dashes, no brackets, no `@s.whatsapp.net` suffix. Country code always included.

```
+60 12-345 6789   →  60123456789
012-345 6789      →  60123456789   (drop the leading 0, prepend the country code)
```

A number without a country code either fails or opens the wrong chat, silently. `wa_digest.py` accepts 6 to 15 digits and rejects anything else, which is why some chats come back with no button rather than a broken one.

## Where the number comes from

WhatsApp identifies every chat by a JID. What the JID looks like decides everything downstream.

| JID shape | `resolution` | `reply_mode` | Meaning |
|---|---|---|---|
| `60123456789@s.whatsapp.net` or `...@c.us` | `jid` | `link` | One-to-one, the number is the JID's local part. Free |
| `1234567890@lid` and the contacts join found it | `contacts_join` | `link` | One-to-one, number recovered from `ContactsV2.sqlite` |
| `1234567890@lid` and the join found nothing | `unresolved` | `copy` | One-to-one, number unknown, no button possible |
| `...@g.us` | `group` | `copy` | Group. Structurally cannot have a link. See below |

### The `@lid` story

A `@lid` chat is an ordinary one-to-one chat where WhatsApp has substituted an internal linked identifier for the phone number, so the number never appears in that record. It is not a corrupted JID and it is not a group.

The digest tries to recover the number by joining against the local `ContactsV2.sqlite`. Measured on a real library: **26 lid chats, 12 recovered, 14 not.** The 14 get `reply_mode: "copy"`.

A lid is not derivable from arithmetic or pattern. Never guess a number, never reuse a number from a similarly named chat, and never construct an `href_prefix` for an unresolved chat. Rule 4 of `SKILL.md`: never fabricate a phone number.

### Measured coverage

Of **22 one-to-one chats** in the default 3 day window on a heavy account, **15 (68%) got a working deep link and 7 did not.** At 7 days it was 37 of 52, the same ratio. That ratio is normal. A board where a quarter of the one-to-one rows copy instead of opening is working correctly.

## Groups cannot have a link

There is no WhatsApp URL that opens a specific existing group with prefilled text. Not an undocumented one, not a differently spelled one. This is structural.

The link that does exist, `https://chat.whatsapp.com/<code>`, is a **group invite link**. It asks the recipient whether they want to join the group. It is a membership mechanism, it cannot carry a message, and clicking your own group's invite link does not open that group with a draft in it. It is a different thing that happens to look adjacent.

The reason is straightforward: a one-to-one deep link works because a phone number is an address the sender already has. A group has no such address, only an internal id that WhatsApp does not expose as a destination.

**So: groups copy. Always.** Unresolvable `@lid` chats copy too. This is the owner's final decision on the behaviour, not an interim workaround, and it does not need relitigating on a future run.

## Explaining it to a user

When someone asks "why can't it just open my group", answer in their language, in about this shape, without apologising for a limitation that is not yours:

> WhatsApp only publishes chat links for one-to-one chats, because a phone number is an address the link can point at. A group has no address like that. The only group link WhatsApp offers is an invite link, which adds a person to the group, and it cannot carry a message. So for groups the button copies your draft instead, and you paste it into the group. You still get the draft, still edit it, and the copy takes whatever you just changed.

Two things worth adding if they push:

- Nothing is lost. Edits made in the textarea are what gets copied, the same as what a link would carry.
- The copy button lands you in the right place anyway, because you paste into the group you have open, which removes the small risk of a link opening the wrong chat.

If they ask whether some other tool can do it: no tool can, because the platform does not expose the destination. Anything claiming otherwise is either using an invite link or automating the WhatsApp client, which this skill deliberately does not do.

## Nothing is ever sent

The button builds a URL or writes to the clipboard. It never sends, never marks a chat as replied, and never drives WhatsApp. The last action belongs to the user, every time. Say this plainly if a user hesitates before clicking the first one.

## Quick checks

- Test a link without touching a real contact: put `whatsapp://send?phone=<the user's own number>&text=test` in the browser address bar. It should open a chat with the user themselves, message prefilled, unsent.
- Button does nothing: `link_style` is `app` on a machine with no WhatsApp Desktop. Switch to `web`.
- Wrong chat opens: the number lost its country code somewhere. Check `phone` in the digest, not the board.
- Chat opens empty: the `href_prefix` did not end in `text=`, so the encoded draft got appended to nothing.
- Button copies when you expected it to open: check `resolution` in the digest. `unresolved` or `group` is working as designed.
