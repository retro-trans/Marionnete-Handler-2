# Shop and account UI — 0.1.11

The user's shop and account screenshots identify four labels outside the
original 793-record inventory. `work/translation/en/shop_account_ui.json`
contains their source labels, complete English targets and native locations.

| Location | English | Native storage |
| --- | --- | --- |
| Shop purchase button | Buy | SHOP_00.PVR, rectangle (180,24)–(212,40) |
| Shop sale button | Sell | SHOP_00.PVR, rectangle (212,24)–(244,40) |
| Account current balance | Balance | Relative string offset at executable 0x5abb0 |
| Account waiting status | Please wait. | Relative string offset at executable 0x5a87c |

Balance is the natural concise English heading for the account's current
balance. Both account labels retain the native Bizin Gothic Bold font and the
0.1.10 lowercase-t correction. Balance is centered at x=37; Please wait.
starts at x=3. Native glyph vertices are checked against the original card's
right edge at x=159. The amount and other account states are unchanged.

Buy/Sell are font glyphs in the original 256×256 shop sprite atlas, rendered
using the same Bizin Gothic Bold source. Their 32×16 slots use proportional
letters, antialiased coverage and the original 4-bit alpha channel. The texture
is edited on the disc, with the same size and ARGB4444 twiddled format. This
requires no Flycast texture replacement. Pixels outside the two slots are
checked byte for byte, including the decorative slogan and shop logos.

`tools/pvr_ui.py` supports only the explicitly checked square, twiddled,
uncompressed 16-bit formats. Its coordinate order follows the existing native
font encoder and is consistent with [Flycast's texture conversion code](https://github.com/flyinghead/flycast/blob/master/core/rend/texconv.cpp).
The original shop texture's full decode/encode round trip must be exact.

The user's reference screenshots are saved in `work/ui/`, with locations and
validation recorded in `shop-account-0.1.11.json`. The shop comparison image
is a native texture preview, not an emulator screenshot. Original Japanese
scripts remain on the source disc; only these four short UI labels are saved.

## Build and test

Inspect the read-only plan:

```text
python tools/build_ui_english.py
```

Add `--validate` for native checks, or `--build` for the cumulative test disc.
Existing output folders are refused. All 793 original translations and their
native draw paths are checked; the new account callers execute their actual
coordinate setup, relative-pointer computation and English dispatch.

Open `work/output/english-0.1.11/Marionette Handler 2 English 0.1.11.gdi` in
Flycast and boot from scratch. A save state restores older executable and
texture memory. The matching CUE keeps the same track layout. Source raw
tracks are never modified. Check Buy and Sell in the shop, then the account
card's label placement and balance amount.

After committing the build sources, package the cumulative release:

```text
python tools/package_vwf.py --retro-trans-tools E:/Projects/retro-trans-tools --version 0.1.11 --build-prefix english --build
```

The local Retro Trans Tools package contains patches for original Tracks 3
and 17, a manifest with hashes, font licenses and instructions. Both patches
are required. No GitHub release is published by this build.
