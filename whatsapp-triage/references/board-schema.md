# Board schema

Loaded on every triage run, with `triage-doctrine.md`. The doctrine decides what goes on the board. This file is how you write it down so it renders and validates on the first try.

## The pipeline

You author one JSON file. `wa_board.py` validates it and injects it into the locked template.

```
boards/board-<date>.json      you write this, and only this
assets/triage-board.html   locked, never edited, never copied by hand
boards/board-<date>.html      what wa_board.py produces
```

The template's only variable is the block inside `<script id="board-data" type="application/json">`. Everything else (CSS, render loop, theme toggle, keyboard nav) is fixed. `assets/example-board.html` is a complete worked board built from a fictional home fragrance business. When a shape is unclear, copy from it rather than inventing.

## Hard layout facts

These come from the template's own comments and its render code, and they are not preferences.

- **The page never scrolls.** `body` is `overflow:hidden`. The left rail scrolls internally; the right panel does not. A block whose content is too tall scrolls inside itself, which is a degraded experience, not a design.
- **The `draft` block is pinned to the right half at full height.** All other blocks stack down the left half. So **at most 3 blocks per row, one of them the draft.** Two prose blocks plus a draft, or a prose plus a list plus a draft, and nothing more.
- **A row with `blocks: []` or no `blocks` key renders fine.** The render loop is `(r.blocks || []).forEach(...)`. Verified. Parked rows may omit blocks entirely to keep the board light.
- **The action button only builds a URL.** `href_prefix` is concatenated with `encodeURIComponent(textarea content)` at click time, so it always carries whatever the user just edited. It never sends anything.
- **Copy actions branch on the absence of `href_prefix`.** A `type: "copy"` action that carries an `href_prefix` will navigate instead of copying. This is the single most common authoring bug.
- **`name` and `snippet` are single line, `white-space:nowrap`, ellipsised.** Overflow is silently cut, not wrapped. The rail is 376px wide.
- **Escaping.** Every field goes through an HTML escaper except two: `legend` and `notice.footer` are injected raw. Put only your own words plus `<br>` in those two, never message content.

## Top level

| Key | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | Header title, for example `Monday 早上 · WhatsApp 分诊台` |
| `tag` | string | no | Small label beside the title. Use it for the window, or omit |
| `meta` | array of `{k, v, hot?}` | yes | Header key/value pairs. Exactly one may set `hot: true` |
| `stamp` | string | yes | Generation time, far right of the header |
| `notice` | object or `null` | yes | The collapsible warning strip. `null` removes the whole strip |
| `bands` | array of `{label, rows[]}` | yes | Rendered in order. A band with zero rows is skipped by the renderer, so just omit it |
| `legend` | string (raw HTML) | no | Small print under the rail. `<br>` allowed |

`notice`: `{badge, title, lead, items[], footer}`. `lead` stays visible while the strip is collapsed, so the most consequential thing goes there. See `triage-doctrine.md` step 9 for when the strip must exist and what belongs in it.

`meta` should always carry the window, a scanned/on board pair, and the one hot Needs You counter. Anything else (money on the table, chats with no button) is optional and earns its slot only if the user would act on it.

## Row

| Key | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique across the board. Becomes DOM ids `p-<id>` and `t-<id>`, so lowercase, digits and hyphens only |
| `name` | string | yes | Display name. Single line, budget about 28 characters |
| `emoji` | string | yes (may be `""`) | Gets its own column. Leaving it inside `name` misaligns every row |
| `tag` | `{label, tone}` | yes | The pill on the left of the row |
| `dim` | bool | no | `true` shortens and fades the row. Parked rows only |
| `flag` | bool | no | `true` shows a red dot after the name, meaning something in this chat is unreadable |
| `num` | string | no | Message count for the window, top right of the rail row |
| `date` | string | no | Last activity, `MM-DD HH:MM` |
| `snippet` | string | no | One line, the reason this chat is on the board. Budget about 40 CJK or 70 Latin characters. Omit on Parked rows |
| `chip` | `{label, tone}` | no | Small pill at the bottom of the rail row. Carries who holds the ball |
| `gauges` | array of `{k, v, hot?, grow?}` | yes | The strip under the panel title |
| `blocks` | array | no | Max 3, at most one draft. May be omitted entirely |

Tones, everywhere they appear: `accent` orange, `wf` amber, `ns` grey, `bl` red, `dn` green. The orange rule in `triage-doctrine.md` step 5 governs which is legal where.

### Canonical gauge set

Four gauges, in this order, on every row. Keep the keys identical across the board so the eye can compare rows.

```json
"gauges": [
  {"k": "类型",   "v": "一对一"},
  {"k": "球在谁", "v": "你", "hot": true},
  {"k": "最后活动", "v": "08-18 08:12"},
  {"k": "读取窗", "v": "08-15 到 08-18, 17 条全读到", "grow": true}
]
```

- `类型` / `Type`: `一对一` or `群组 (7 人)`, from `kind` and `participants_seen`.
- `球在谁` / `Ball`: `你` or `对方`. `hot: true` only on Needs You rows.
- `最后活动` / `Last`: from `last.at`.
- `读取窗` / `Read`: always `grow: true`, it is the widest value. State the range and the honesty: `17 条全读到`, `14 条读到 12 条`, `8/16 起 (前段未读)`. This is where transcript truncation becomes visible to the user.

## Blocks

```json
{"kind": "prose", "title": "...", "text": "...", "warn": {"title": "...", "text": "..."}}
{"kind": "list",  "title": "...", "items": ["...", "..."]}
{"kind": "draft", "title": "...", "note": "...", "text": "...",
 "action": {"type": "link"|"copy", "label": "...", "label_dirty": "...",
            "href_prefix": "...", "hint": "..."}}
```

- **prose** is the situation. Two to four sentences, the state of play and what is actually at stake. `warn` is optional and renders as a red box: use it for anything unreadable or anything you could not verify.
- **list** is the timeline. Each item is `MM-DD HH:MM` plus what happened, oldest first. Six to eight items maximum; it is context, not a log.
- **draft** is the reply. `note` explains why the draft is written this way and which brackets need a human. `text` is the message itself. Omit `text` to render the empty state, in which case `note` carries the whole explanation and there must be no `action`.

## Worked row: one-to-one, link action

```json
{
  "id": "sity-nurhaliza-wrong-item",
  "name": "Sity Nurhaliza",
  "emoji": "🔥",
  "tag": {"label": "要你动", "tone": "accent"},
  "dim": false,
  "flag": false,
  "num": "17",
  "date": "08-18 08:12",
  "snippet": "买 Pandan Wangi 收到 Kopi Tarik, 已经第三天没人回她",
  "chip": {"label": "球在你", "tone": "accent"},
  "gauges": [
    {"k": "类型", "v": "一对一"},
    {"k": "球在谁", "v": "你", "hot": true},
    {"k": "最后活动", "v": "08-18 08:12"},
    {"k": "读取窗", "v": "08-15 到 08-18, 17 条全读到", "grow": true}
  ],
  "blocks": [
    {
      "kind": "prose",
      "title": "最新状况",
      "text": "订单 SHP-2408-11973, 她买两支 Pandan Wangi 100ml, 收到的是 Kopi Tarik, SKU 出错。她 08-15 就发了开箱照, 我们三天没回, 08-17 她在 Shopee 开了 dispute, 08-18 早上说要 post 上 Threads。事实清楚, 照片对得上, 没有争议空间。"
    },
    {
      "kind": "list",
      "title": "时间线",
      "items": [
        "08-14 14:22 下单 SHP-2408-11973, RM 187.40",
        "08-15 11:03 她发开箱照, 瓶身标签是 Kopi Tarik",
        "08-16 全天无回覆",
        "08-17 09:41 她在 Shopee 开 return dispute",
        "08-18 08:12 「我 post 上 Threads 咯」"
      ]
    },
    {
      "kind": "draft",
      "title": "回覆草稿",
      "note": "她要的不是解释, 是有人认错。第一句直接认, 不铺垫。补寄加不退货是本来就有的 SOP, 所以我填死了。语气刻意短, 长的道歉在这个点上像在拖。",
      "text": "Sity, 是我们出错, 对不起, 拖了三天更加不应该。Pandan Wangi 100ml 两支我今天下午 ship 出去, tracking 一出马上发你, Kopi Tarik 那支你留着不用退。Shopee 那边的 dispute 你先别撤, 等货到你手上确认没问题再说。",
      "action": {
        "type": "link",
        "label": "用草稿开启 WhatsApp",
        "label_dirty": "用你改的版本开启",
        "href_prefix": "whatsapp://send?phone=60123456789&text=",
        "hint": "发之前确认仓库今天真的出得了货, 讲了做不到会更难收。"
      }
    }
  ]
}
```

## Worked row: group, copy action, with a gap

```json
{
  "id": "guangzhou-ceramic-supplier",
  "name": "广州陶瓷厂 · 采购群",
  "emoji": "🏭",
  "tag": {"label": "要你动", "tone": "accent"},
  "dim": false,
  "flag": true,
  "num": "41",
  "date": "08-17 22:09",
  "snippet": "报价 PDF 读不到, 而且他们欠你的确认已经过期 4 天",
  "chip": {"label": "球在你", "tone": "accent"},
  "gauges": [
    {"k": "类型", "v": "群组 (7 人)"},
    {"k": "球在谁", "v": "你", "hot": true},
    {"k": "最后活动", "v": "08-17 22:09"},
    {"k": "读取窗", "v": "08-05 到 08-18, 41 条读到 40 条", "grow": true}
  ],
  "blocks": [
    {
      "kind": "prose",
      "title": "最新状况",
      "text": "第二批 1,200 pcs, 你 08-13 要他们 08-14 前确认单价和船期, 第 4 天了还是只有「我们在核」。这批货接 10 月大促, 海运 26 天, 再拖两周备货就断。",
      "warn": {
        "title": "读不到 / 要小心",
        "text": "那份 AMB-Q3-CERAMIC-v4.pdf 我只读到档名, 附件本体没同步过来, 里面的价钱和 MOQ 完全不知道。草稿里不敢引用任何数字。"
      }
    },
    {
      "kind": "draft",
      "title": "回覆草稿",
      "note": "供应商这条线不需要客气, 需要一个具体时间点和一个具体后果。只问两个数字, 问三个以上他们又会整包拖。",
      "text": "Chen 姐早, v4 那份我收到了。麻烦今天下班前直接在群里打两个数字给我: 1,200 pcs 的单价, 加最早的开船日期。10 月促销的备货窗口只到 8 月 22 号, 过了这天我这边要转另一家备一批, 不想走到那步。",
      "action": {
        "type": "copy",
        "label": "复制草稿",
        "label_dirty": "复制你改的版本",
        "hint": "群组没有号码可以开链接, 复制后自己贴进采购群。"
      }
    }
  ]
}
```

Note what changes for a group: no `href_prefix`, `type: "copy"`, a hint that says why, and only two blocks because the prose already carries the timeline.

## Worked row: parked

```json
{
  "id": "shopee-seller-broadcast",
  "name": "Shopee MY 卖家公告群",
  "emoji": "📢",
  "tag": {"label": "无待办", "tone": "ns"},
  "dim": true,
  "flag": false,
  "num": "38",
  "date": "08-18 07:30",
  "chip": {"label": "球在对方", "tone": "ns"},
  "gauges": [
    {"k": "类型", "v": "群组 (广播, 只读)"},
    {"k": "球在谁", "v": "对方"},
    {"k": "最后活动", "v": "08-18 07:30"},
    {"k": "读取窗", "v": "08-11 到 08-18, 38 条全读到", "grow": true}
  ],
  "blocks": [
    {
      "kind": "draft",
      "title": "回覆草稿",
      "note": "官方单向广播, 群里没人 @ 你, 38 条全是活动报名和 banner 规格通知, 没有一条要回。不写草稿。"
    }
  ]
}
```

No `snippet`, `dim: true`, and a note-only draft that says why nothing is owed. For a row nobody will ever open, drop `blocks` entirely.

## Validation, as `wa_board.py` enforces it

Exit `0` valid and written, `2` usage or file error, `3` validation failure. On `3` the script prints the JSON path of every failure and writes nothing, so fix and rerun rather than editing the HTML.

**Fails the build**

| # | Rule |
|---|---|
| 1 | The file parses as one JSON object. No trailing commas, no comments, no JavaScript |
| 2 | `title`, `meta`, `stamp`, `bands` present. `notice` present and either an object or `null` |
| 3 | At least one band with at least one row |
| 4 | `row.id` present, unique board wide, matching `^[a-z0-9][a-z0-9-]*$` |
| 5 | `row.name` present and non-empty |
| 6 | Every `tone` is one of `accent`, `wf`, `ns`, `bl`, `dn` |
| 7 | `accent` appears only in the first band, in `tag.tone` and `chip.tone` |
| 8 | At most one `meta` entry with `hot: true`, at most one gauge per row with `hot: true` |
| 9 | `blocks` has at most 3 entries and at most one of `kind: "draft"` |
| 10 | `kind` is one of `prose`, `list`, `draft` |
| 11 | `prose` has `title` and `text`. A `warn` has both `title` and `text` |
| 12 | `list` has `title` and an `items` array of strings |
| 13 | `draft` has `title`. With non-empty `text` it must have `action`. Without `text` it must have `note` and must not have `action` |
| 14 | `action.type` is `link` or `copy`, and `label`, `label_dirty`, `hint` are all present and non-empty |
| 15 | `link` has an `href_prefix` ending in `text=`, since the renderer concatenates the encoded draft straight onto it |
| 16 | `href_prefix` matches `whatsapp://send?phone=<digits>&text=` or `https://wa.me/<digits>?text=`, digits only, 6 to 15 of them, no `+` |
| 17 | `copy` has no `href_prefix` |
| 18 | No field contains a raw control character |

**Warns, and still builds**

| # | Rule |
|---|---|
| 19 | More than 20 rows, or more than 5 rows in the first band |
| 20 | `name` over 28 characters, `snippet` over 70, `tag.label` over 12, `chip.label` over 14, a non `grow` gauge value over 20. CJK counts roughly double against the rail width, so a 40 character Chinese snippet is already at the limit |
| 21 | A row with `dim: true` outside the last band, or a `snippet` on a `dim` row |
| 22 | `emoji` repeated at the start of `name`, which renders it twice |
| 23 | `legend` or `notice.footer` containing a tag other than `<br>` |
| 24 | A band whose `rows` array is empty, which the renderer silently skips |

Rule 16 checks shape only. Nothing in the JSON tells the validator whether a row is a group, so **not emitting a link action for a group is your job**, per rule 4 of `SKILL.md` and the `reply_mode` field the digest already computed. Copy `href_prefix` from the digest verbatim and never build one yourself.
