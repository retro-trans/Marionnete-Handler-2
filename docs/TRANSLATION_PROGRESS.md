# English translation — 0.1.3

The first **160 of 793 inventoried game entries (20.2%)** are translated into
English. This release adds menu rows 81–160 to the previous 80 messages and
includes the VWF patch. The 773 separate browser/network entries, dialogue and
image-based text remain untranslated. Image-based text is not included in the
793-entry count.

## Included in this release

Batch 001 covers shop transactions, equipment restrictions, login/logout,
memory-card errors and naming prompts. Batch 002 adds battle/reset confirmations,
user registration, memory-card operations, controller status, display adjustment,
timer/alarm messages and six one-line port/socket labels.

The editable batches are `work/translation/en/ui_batch_001.json` (rows 1–80)
and `ui_batch_002.json` (81–160). Row numbers use the menu category in
`work/ui/text_inventory.json`, sorted by original file offset. Japanese source
remains on the original disc and is read in memory. The cumulative binding
report is `work/ui/english_0.1.3_inventory.json`.

The English glossary now contains 33 approved terms. These spellings are project
translations of short game UI terms. The [official developer page](https://www.micronetclub.co.jp/games/index.htm)
establishes game identity, not official English spellings. No named character or
location appears in these slices; research their records before translating a
later occurrence. The existing search did not establish a character wiki.

## Test image and patch

Open `work/output/english-0.1.3/Marionette Handler 2 English 0.1.3.gdi` to test
the new image. A matching CUE is supplied. Both reference the original tracks
01–16 and the new English Track 17. Preserve the folder structure.

`work/output/release-0.1.3/` contains the xdelta, build manifest, validation
record and checksums. In Retro Trans Tools manual xdelta mode, apply this patch
to the **original Track 17 BIN**, save a new file, and reference that file from
a copied CUE/GDI. This cumulative patch includes VWF and both English batches.
The manifest pins the source and target hashes. Shareable assets contain no
game binaries. Automatic multitrack GD-ROM/CHD conversion remains outside the
current tool contract. Earlier output folders are retained.

## Meaning and runtime composition

The translator and reviewer each examined 88 source rows for the new 80-row
slice: rows 81–160 plus context 77–80 and 161–164. The independent review and
primary direction check led to two corrections: the stop confirmation says
“Stop anyway?” and the elapsed-time suffix avoids singular/plural disagreement.
Batch 001 retains its original 84-row review. Terminology checks follow meaning
review; controls and newline counts are preserved.

Native caller inspection confirms that the live price precedes row100, with
no formatter-added currency symbol. Four insertion prefixes precede a destination
label and the shared row119 suffix, including both pointer aliases. The purchase
confirmation assembles row144, a one-line destination label, then row145. Timer
and alarm callers distinguish elapsed duration from a reached clock time.
Caller offsets and uncertainty notes are recorded in batch 002.

Some composed messages are still mixed-language: insertion labels 163–170,
Port D labels 161/162, and timer hour/minute snippets remain Japanese outside
this slice. Retained source omissions are flagged in rows 87, 88, 91, 131,
149, 150 and 154. Earlier equipment-context flags for rows 1/4, 55 and 57 remain.

## Build validation and limits

The cumulative 160-message bank occupies 6,999 original bytes. The complete
English strings use 6,062 bytes and retarget 164 verified pointer locations.
Individual source slots do not limit the translation. The executable length
and untranslated records stay intact. Future dialogue requires separate
relocation storage under the project rules.

The limited SH-4 harness executes native dispatch for every message in font
modes 1 and 4 (320 cases), three numeric block warnings, ten assembled card
messages, and three live-price confirmations. The original default font loader
loads 613 codes over seven resumable passes, covering all 61 required visible
English characters. Spaces retain the original blank fallback of 20 pixels.
BIOS glyph ink metrics are simulated and platform services are stubbed.

The generated executable is read back from the raw track. Full-track verification
checks the ten intended changed sectors, unchanged bytes elsewhere, regenerated
EDC/ECC, and all 17 GDI references. Retro Trans Tools encodes and decodes the
patch and compares the complete reconstructed Track 17.

**Emulator/hardware playtesting and actual screen fit remain outstanding.**
Cached-font mode 1 needs measured BIOS advances and textbox bounds. Observed
source lines reach 20 characters; English reaches 41. The native small-font
table gives a maximum of 348 pixels, but that does not establish cached-font
fit. These measurements are not an approved UI character limit.

## Continue or reproduce

Next: menu rows **161–240**, including the remaining runtime destination labels.
Read surrounding context, preserve controls and glossary spellings, and keep
source text out of saved scripts.

Run `python tools/build_english.py --plan-only` for bindings and sample text,
or omit `--plan-only` to also run the native drawing checks. After inspecting
the plan, use `--build`. Existing output folders are refused. Use
`--verify-existing` for full-track and descriptor verification; after inspecting
that output, add `--report` to save evidence. This reuses native drawing evidence
only when the exact target program and translation revision match. Add
`--version 0.1.2` to reproduce or verify the previous English release.

Commit sources before packaging. With Python 3.12+ and a local Retro Trans Tools
checkout, inspect the packaging plan and then add `--build`:

```text
python tools/package_vwf.py --retro-trans-tools PATH --build-prefix english --version 0.1.3 --language en
```

Any changed game bytes require a new build version and change-log entry.
