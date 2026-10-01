# UI text assessment

Assessment version: 0.1.0  
Date: 2026-10-01  
Status: Discovery only; no translated release or patched image.

The workspace initially contained the project instructions and the original
17-track BIN/CUE game image. It did not contain extracted text, a glossary,
translations, screenshots, or a patching pipeline. The high-density disc
filesystem contains 299 files. Readable game text is embedded in
`/1ST_READ.BIN`; browser messages are in `/DPETC/MESSAGE.INI`.

## Translation scope found

| Area | Japanese entries |
| --- | ---: |
| Menus, prompts, help, and descriptions | 560 |
| Training and programming labels | 84 |
| Equipment statistics and customization | 40 |
| Battle result labels | 13 |
| Tournament titles | 28 |
| Consumable names | 12 |
| Equipment preset names, including repeated presets | 56 |
| **Game text subtotal** | **793** |
| Network/browser message file | 773 |
| **Total located entries** | **1,566** |

Exact source-string deduplication gives **732 distinct game strings** and
**766 distinct browser messages**, for **1,498 distinct strings** in these
two sources. Formatting, whitespace, and control commands are retained when
comparing strings. A multiline string counts as one entry. These are readable
Japanese text records; individual visibility and layout have not been verified
in an emulator. The large game pool includes menu text and explanatory text,
not just short menu labels.

## Evidence and method

- Read the ISO directory from the raw MODE1/2352 sectors without changing the
  image. The high-density area starts at LBA 45000; file contents are located
  in the final data track, whose stored pregap is included in the LBA mapping.
- Decode strings using CP932. Review fixed-stride title/name tables and
  NUL-terminated game string pools; preserve line breaks within each entry.
- Use absolute pointer references as supporting evidence where present.
  Some text is accessed through tables or relative references, so an absent
  absolute reference does not mean a string is unused.
- Parse all 786 numbered browser-message assignments. Of these, 773 contain
  Japanese and 13 do not. Seven Japanese entries repeat exactly.
- Reject code, numeric tables, and character-encoding/font data that happen
  to decode as Japanese. Specifically exclude two floating-point fragments
  from the early game pool.
- Save source-free metadata in `work/ui/text_inventory.json`: offsets,
  categories, source lengths, message IDs, pointer locations where available,
  and hashes. Full Japanese source scripts are not exported.

The initial byte-pattern scan produced many false positives, especially in
the browser executable. Those raw candidate counts are not translation counts.

## Limits and next work

This is a **lower bound**, not a complete census of everything displayed by
the game. The disc contains 65 PVR/PVM texture files; that is a file count,
not a count of UI labels. Text baked into those textures and GIF/JPEG artwork
requires visual inspection and is not included above. Additional browser
executable strings and page scripts are also excluded from the reviewed count.
Custom encodings or packed text would require further investigation.

The identified strings can be translated linguistically. Shipping those
translations also requires a glossary, target language, font/rendering work,
pointer or table relocation where needed, and emulator checks for wrapping
and control-code behavior. Source lengths in the inventory describe the
original data; they are not an approved translation byte limit.

No source track was modified, no patch was produced, and Retro Trans Tools
compatibility has not been tested. Every future release must satisfy the
project's Retro Trans Tools requirement.

## Reproduce

Dry run, with counts only:

```text
python tools/inspect_disc_text.py --reviewed
```

After reviewing the output, save the source-free inventory:

```text
python tools/inspect_disc_text.py --reviewed --report
```

The reviewed offsets apply to this image revision. Source hashes are recorded
in the inventory to identify it; offsets must be reassessed for another revision.
