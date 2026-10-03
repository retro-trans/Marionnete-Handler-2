# Shop descriptions — 0.1.13

## All shop categories

Build 0.1.13 applies the same native help background and wrapping to all five
shop categories, including the Option description shown in the user's new
screenshot. Coverage comes from the five native descriptors at `0x921d0`, each
20 bytes long. Their description table pointers resolve to these reviewed rows:

| Category | Description rows | Native selections |
| --- | --- | --- |
| Marionette Units | 312–318 | 7 |
| Modification Parts | 324–334 | 11 |
| Weapons / Options | 319–321 | 3 |
| Maintenance Supplies | 322–323 | 2 |
| Used Parts | 312 (shared existing descriptor) | 1 |

There are 24 selections and 23 distinct descriptions. The existing shared
mapping in the fifth descriptor is retained. The translated targets are in
`work/translation/en/shop_description_layout_0.1.13.json`. Wrapping preserves
all words, punctuation, leading/trailing newlines and paragraph breaks,
including the blank line in Maintenance Kit. Headers are checked too.

Every category uses the 320×252 native background at the shop window's position,
with the existing fade and draw depth. All 24 selections are executed through
the actual shop caller; additional cases test half and fully faded descriptions
in each category. All 23 descriptions are also drawn through mode 3. Checks
verify source-table coverage, compiled pointers and text bounds. Bizin glyph
records and the six-pixel space remain unchanged from 0.1.12.

Boot `work/output/english-0.1.13/Marionette Handler 2 English 0.1.13.gdi`
from scratch. The cumulative Retro Trans Tools package is in
`work/output/release-0.1.13/`. Native and disc verification are automated;
fresh Flycast visual confirmation of the new coverage remains pending.

## Original parts-only fix in 0.1.12

The user's CPU screenshot shows the English description extending into the
account card. The actual shop caller at executable offset `0x58b8e` selects
cached font mode 1, which already draws proportionally. Bizin Gothic Bold has
similar Latin ink widths, and missing ASCII spaces advanced 20 pixels. Those
wide spaces and preserved Japanese line breaks caused the horizontal overflow.

Build 0.1.12 uses six-pixel ASCII spaces and wraps all eleven parts descriptions
at a 300-pixel advance limit. Every word, punctuation mark and original storage
length is preserved. Targets are in
`work/translation/en/shop_description_layout.json`; the original reviewed
translation batches remain intact. Bizin's embedded bitmap records, including
the corrected lowercase t, are unchanged.

The parts help background is now a native rectangle 320 pixels wide and 252
pixels tall, behind the text at the existing shop window position. It follows
the description fade and appears only for the parts category. Other categories
keep their existing background. The new rectangle uses the game's existing
untextured draw routine; no emulator texture replacement is involved.

The renderer audit also found a separate fixed cached mode: mode 3 and the
scrolling ticker called `0x8100`. Their two literals now point to the native
proportional renderer at `0x7f64`. Its drawing and measurement helpers agree
on six-pixel ASCII spaces; fullwidth Japanese spaces and other missing glyphs
retain their original fallback. The abandoned fixed renderer's 420-byte range
stores the small helpers. The following routine at `0x82a4` is preserved.

Validation executes all eleven descriptions in mode 3 and through the actual
shop mode-1 caller, including source-table pointer selection, font setup and
native coordinate calculation. All text fits the enlarged rectangle at
`[70,150,390,402]` for the captured screen layout. Background depth is 129 and
text depth 130 for a window depth of 100. Three fade levels and all four other
categories are checked. Native drawing and measurement distinguish W (14px),
i (11px) and spaces (6px); the scrolling caller uses the same advances.

The complete build checks all 793 messages, 708 embedded glyph records, VQ
compression, startup preservation, account callers, ISO entries, sector EDC/ECC
and all 17 GDI references. A fresh Flycast visual check remains pending.

Boot `work/output/english-0.1.12/Marionette Handler 2 English 0.1.12.gdi`
from scratch. An older emulator state restores its older code and font.
The cumulative two-track patch is in `work/output/release-0.1.12/` and is
validated with Retro Trans Tools.
