# English translation — first batch, 0.1.2

Target language: English. The first 80 system/shop messages have been translated
and reviewed against the original disc. This covers 80 of the 793 inventoried
game entries (10.1%). None of the 773 separate browser/network entries are
translated yet. Image-based text remains outside that inventory.

## What is included

- Purchases, sales, stock limits, equipment restrictions and entry requirements.
- Save/load/copy/delete errors and memory-card warnings.
- Login/logout, naming prompts, timers and alarms.
- The previous 0.1.1 VWF changes, included in the English test track.

Examples: “Not enough material. / Buy more at the shop.”, “Marionette purchased.”
and “The memory card needs / [number] more free blocks.” The number in the last
message remains a live game value. Source-code inspection confirms it is the
difference between required and available blocks, rather than a total capacity.

## Files and test build

`work/translation/en/ui_batch_001.json` contains the editable English text,
review status and context notes. Entries 1–80 correspond to the first 80 menu
records sorted by original file offset in `work/ui/text_inventory.json`.
`work/ui/english_batch_001_inventory.json` binds every translation to its source
ID/hash, new address, pointer locations and display-length measurements. The
Japanese source stays on the original disc and is read in memory for review.

`work/glossary/en.json` establishes 26 terms, including Marionette, P-Card,
Repair Kit, MARCS V2 and equipment categories. Spellings are project translations
of the game's short UI terms. The [official developer page](https://www.micronetclub.co.jp/games/index.htm)
confirms game identity. No character/location names occur in this batch; their
glossary records must be researched before translating a later occurrence.
The glossary search did not establish a relevant character wiki.

Open `work/output/english-0.1.2/Marionette Handler 2 English 0.1.2.gdi` to test
the English image. A matching CUE is also supplied. Both reference the original
tracks 01–16 and the new English Track 17. Keep the folder structure intact.

The shareable release assets are in `work/output/release-0.1.2/`: one xdelta,
`BUILD-MANIFEST.json`, `VALIDATION.json`, and `SHA256SUMS.txt`. In Retro Trans
Tools manual xdelta mode, apply the patch to the **original Track 17 BIN** and
save a new file, then reference that file from a copied CUE/GDI. This is a full
patch from the original and already includes VWF. The manifest identifies its
exact source and target hashes. No game binaries belong in the shareable release.
Automatic GD-ROM/multitrack CHD conversion is outside the current tool contract.

## Review and validation

The translation and its meaning reviewer each examined 84 source rows for the
80-row slice: all rows in the slice and adjacent rows 81–84. The reviewer found
no required meaning correction. Terminology validation runs after that review.
All newline counts and inline control/placeholder tokens are retained. Each
original text hash and every discovered pointer is checked before patching.

The first 80 original messages form a contiguous 3,158-byte bank. Complete
English translations use 2,724 bytes, so the builder repacks the whole bank and
retargets 83 pointer locations. No string is trimmed to its individual source
slot. The executable size and all other text records remain unchanged. Dialogue
is not in this batch; future dialogue needs its own relocation storage, as the
project rules require.

The SH-4 harness executes the original default font loader over seven resumable
passes, producing 613 cache codes. All 54 visible characters required by this
batch are present. Spaces use the original blank fallback of 20 pixels.
It executes all 80 translated messages through native dispatch in font modes
1 and 4 (160 cases), plus three composed numeric warnings. BIOS glyph generation
and resulting ink metrics are simulated; platform services are stubbed. The build reads
the entire patched executable back from the generated raw track and checks the
intended bytes. Edited sectors receive regenerated EDC/ECC. Retro Trans Tools
then encodes and decodes the patch and verifies the complete target Track 17.

**Emulator/hardware playtesting remains outstanding.** In particular, the
popup uses cached-font mode 1, so its actual BIOS font advances and textbox
boundaries need screen verification. The observed maximum source line in this
batch is 20 characters; English reaches 41 characters. These are measurements,
not an approved character limit. The small-font metric table gives a maximum
English line width of 348 pixels, but it cannot establish the cached-font fit.

Context flags remain for the omitted item in messages 1/4, whose unit is
overweight in message 55, and unit/model armor compatibility in message 57.
Their current wording is recorded for review rather than treated as verified
equipment-screen behavior.

## Continue or reproduce

The next menu slice is rows 81–160, with adjacent context read before translating.
Preserve terminology and controls, and keep source text out of saved scripts.
Check the existing translations before starting the next slice to avoid repeats.

Run `python tools/build_english.py` to inspect a read-only build plan. After
reviewing its output, add `--build`. Existing output folders are refused.
Use `--verify-existing` to check the full existing track, sector parity and all
17 GDI references; add `--report` after reviewing that output to save evidence.
Commit the source files before packaging. With Python 3.12+ and a local Retro
Trans Tools checkout, first dry-run and then add `--build` to:

```text
python tools/package_vwf.py --retro-trans-tools PATH --build-prefix english --version 0.1.2 --language en
```

Changing target game bytes requires a new version. The previous 0.1.1 outputs
are kept separately.
