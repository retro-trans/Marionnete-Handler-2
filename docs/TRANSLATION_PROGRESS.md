# English translation — 0.1.4

**All 793 inventoried game records are translated into English (100%).**
This release adds the remaining 633 records to the earlier 160. It includes
menus, programming help, training labels, equipment statistics, battle results,
tournament titles, consumable names and preset names, together with VWF.

This count is the reviewed inventory, not a census of all game artwork.
The 773 separate browser/network messages, uncounted texture text, additional
ASCII-only symbols and player-created text are outside this request.

## Translation and review

The editable text is in `work/translation/en/`: seven `ui_batch_*.json`
files cover menu rows1–560, and three `game_batch_*.json` files cover561–793.
`tools/game_text_rows.py` defines this stable order: menus sorted by source
offset, then all other game categories sorted by source offset. The final slice
contains73 records; all other slices contain80. Every target has a source ID,
hash and compiled location in `work/ui/english_0.1.4_inventory.json`.
Japanese source scripts remain on the original disc and are read in memory.

All ten slices have independent meaning review. The reviewers examined885
rows across793 slice records, including overlapping contextual reads. The new
slices record restored comparative/ongoing-action meanings and required Yes/No
and step-count spacing. Source omissions and uncertainty notes remain attached
to the affected rows. Controls and original newline counts are preserved.

The glossary has45 approved terms, including the seven source Latin robot
model names. Valkyrje and Gryps retain the disc spelling. Dream Passport is
corroborated by [Sega's official Dreamcast page](https://www.sega.jp/history/hard/dreamcast/).
Miyata Models is a project romanization, McNET retains the source spelling,
and WMA remains an unexpanded acronym. No named human requires a gender or
personality inference. Meaning fixes precede glossary normalization.

## Test image and Retro Trans Tools patch

Open `work/output/english-0.1.4/Marionette Handler 2 English 0.1.4.gdi`.
A matching CUE is provided. Keep the workspace structure: both descriptors
reference original tracks01–16 and the new English Track17.

The shareable patch and manifest are in `work/output/release-0.1.4/`.
In Retro Trans Tools manual xdelta mode, apply the patch to the **original
Track17 BIN**, then reference the reconstructed file in a copied CUE/GDI.
This patch is cumulative and includes all793 translations and VWF. Exact source
and target hashes are pinned in the manifest. The package contains no game
binaries. Automatic multitrack GD-ROM/CHD conversion is outside the current
tool contract. Earlier release folders remain available.

## Storage and runtime verification

The builder retains executable length and directory layout. Complete strings
are distributed across verified text banks, name-field padding and initialized
executable tail space. It retargets625 menu pointers. Another137 records use
exact old-address lookup because their consumers use base-plus-offset addresses;
odd-valued addresses are preserved. Lookup hooks cover native dispatch6090,
width measurement63e4 and the independent aligned renderer6460.

Six tournament titles exceed their32-byte record name fields. Reserved copied
display handles resolve those fields to complete English titles. Native code
copies the whole68-byte record, including the handle, while numeric fields
remain intact. No title is trimmed to its old field size. These internal handles
are implementation data; editable translations retain the complete English.

The lookup uses236 bytes of the old fixed renderer, whose three callers VWF
already redirects, and a source-checked tail table below the BSS boundary.
The actual startup clearing/copy routine was executed and leaves every patched
region intact. Bracket conversion now selects loaded fullwidth bracket glyphs.

Validation passed793 native message dispatch cases,137 old-address lookups,
six actual copied tournament records,233 width measurements,56 aligned-render
equivalence cases and14 numeric compositions. The default font loader produces
613 glyph codes over seven resumable passes, covering73 visible English
characters. Spaces keep the native blank20-pixel fallback. BIOS ink metrics
are simulated; platform services are stubbed.

Full-track verification found31 edited sectors, valid regenerated EDC/ECC,
unchanged bytes elsewhere and all17 GDI references intact. Retro Trans Tools
encodes and decodes the patch and compares the complete reconstructed Track17.

**Emulator/hardware playtesting and actual screen fit remain outstanding.**
Scrolling hints, popup bounds, long tournament titles and positioned statistic
labels need visual checks with real font metrics. The reported lengths and
small-font advances are measurements, not approved UI limits.

## Reproduce

Inspect the read-only plan first:

```text
python tools/build_full_english.py --plan-only
```

Omit `--plan-only` for the complete read-only native validation. After inspecting
the plan, use `--build`; existing output folders are refused. Use
`--verify-existing` for track/descriptor read-back, and add `--report` only
after inspecting that output to save evidence. Earlier builders remain available
for0.1.2/0.1.3 reproduction.

Commit source files before packaging. With Python3.12+ and a local Retro Trans
Tools checkout, inspect this plan and then add `--build`:

```text
python tools/package_vwf.py --retro-trans-tools PATH --build-prefix english --version 0.1.4 --language en
```

Any changes to compiled game bytes require a new version and change-log entry.

The latest font build is **0.1.9**, with corrected embedded Bizin Gothic Bold loading. All 793
translations remain complete. Native message checks now use the real generated
font's cached widths. See `docs/HD_FONT.md` for font coverage and fresh-boot
instructions. Its Retro Trans Tools package requires both Track 3 and Track 17;
use `--version 0.1.9` when packaging this cumulative English build. The user's
0.1.8 state confirmed that its filename loader fell back to the BIOS font;
0.1.9 opens the fixed font extent independently of the current directory.
