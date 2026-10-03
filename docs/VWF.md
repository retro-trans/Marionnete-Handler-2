# Variable-width font — test build 0.1.1

Latest English build: **0.1.14**, with all 144 editor/palette help messages
wrapped in a taller native tooltip. See [program help notes](PROGRAM_HELP.md).
It retains the **0.1.13** wrapped descriptions and native help
backgrounds across all five shop categories. In **0.1.12**, the earlier claim that all remaining fixed
cached text was covered missed mode 3 and the scrolling caller; those now use
the proportional renderer too. ASCII spaces use six pixels in drawing and
measurement. The shop already used mode 1; its descriptions now have narrower
spaces, English line wrapping and a taller native background. See
[shop description notes](SHOP_DESCRIPTIONS.md). This retains embedded Bizin
Gothic Bold and all 793 English records. The historical 0.1.1 notes below
describe the original patch.

This build extends the game's existing proportional fonts to the remaining
fixed cached-font text mode and to integer/decimal readouts. Numeric measurement
now uses the same glyph advances as drawing, so right-aligned values retain
their intended right edge. No translation is included.

The small Latin atlas already has variable widths. Its 95 printable ASCII
metrics are recorded in `work/ui/vwf_metrics.json`; the native renderer adds
2 pixels of tracking. Larger text uses the original runtime Dreamcast BIOS
glyph cache, including its left bearings and advances. This patch does not
replace the BIOS font or add accented Latin/Vietnamese glyphs. A future custom
font can reuse this proportional pipeline but will need new glyph coverage.

## Test or apply

The local test set is `work/output/vwf-0.1.1/`. Open
`Marionette Handler 2 VWF 0.1.1.gdi` in a Dreamcast emulator. The companion
CUE is supplied for tools accepting this original BIN/CUE layout. Both point
to original tracks 01–16 and a separate patched Track 17; keep the workspace
folder layout intact. The GDI retains raw-sector offsets for stored pregaps.

The shareable patch is in `work/output/release-0.1.1/`. It includes the xdelta,
standard `BUILD-MANIFEST.json`, `VALIDATION.json` and `SHA256SUMS.txt`.
Retro Trans Tools is used to encode, decode and validate the patch against the
entire 48,300,672-byte Track 17. Only patch assets and metadata belong in a
shared release; complete game tracks stay in the private test folder.

In Retro Trans Tools' manual xdelta mode, select the **original Track 17 BIN**,
the supplied xdelta and a new output filename. Keep all the other tracks and
update a copy of the CUE/GDI to reference that filename. Do not select the CUE,
a merged image or a CHD as this patch's source. Retro Trans Tools' current
release contract does not support automatic GD-ROM/multitrack CHD conversion.
The standard manifest is ready for a future hosted release; no release has
been published or added to a remote catalog.

Before considering this production-ready, boot the test set and check menus,
dialogue, numeric readouts, cursor positions, Japanese text, and both text
orientations. There is no emulator boot/playtest evidence yet.

## Rebuild

1. Place the original 17 BIN tracks and CUE in the repository root.
2. Run `python tools/validate_vwf.py` and review its output, then run it with
   `--report` to save validation evidence.
3. Run `python tools/build_vwf.py` and review the planned byte changes, then
   run it with `--build` to create a new test folder. Existing builds are
   refused. Optional `--metrics work/ui/vwf_metrics.json` adjusts the native
   small-font widths; changes producing different bytes require a new version.
   Verify the result with `python tools/validate_vwf.py --built --report`.
4. Commit the tools/documentation/metrics, excluding source images and outputs.
5. With Python 3.12+, run `tools/package_vwf.py --retro-trans-tools PATH` to
   review the release plan, then add `--build`. Use an actual local checkout
   of [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools).
   Its verified bundled xdelta engine is sufficient; no network is required
   when that bundle is available. Existing release folders are refused.

The inspection, patch builder and instruction harness require only Python's
standard library. Optional SH-4 disassembly requires 64-bit Python and
Capstone 5 with SH support, installed under `tools/vendor`.

## Patch map and evidence

All offsets below are inside the original `/1ST_READ.BIN`, loaded at
`0x8c010000`. Source SHA-256:
`4526090cb90840370518beb404fe1ec45c6aa20ef0247c46134573a595a969bf`.

| File offset | Change |
| --- | --- |
| `0x4f78–0x50df` | Equivalent ASCII-to-CP932 table converter plus two measurement helpers, using 332 of 360 existing bytes |
| `0x5cda`, `0x5da0` | Integer measurement hook and helper address |
| `0x5eea`, `0x5fc0` | Decimal measurement hook and helper address |
| `0x5db8`, `0x5fd8` | Numeric draw calls use proportional renderer `0x7f64` |
| `0x639c` | Font mode 4 uses proportional renderer `0x7f64` |

The converter preserves all legacy mappings, including the backtick icon
code `0x89fc`, and adds `{`, `|`, `}`, `~`. Bytes outside printable ASCII still
map to the original fallback. No executable growth, memory relocation, ISO
directory update, text rewriting or texture replacement is needed.
Modified sector LBAs are 548203–548206. Each edited raw MODE1 sector retains
its header and receives regenerated EDC and P/Q ECC.

`work/ui/vwf_validation.json` records a limited SH-4 instruction harness:
512 converter checks, 95 cached glyph/renderer checks, fallback checks,
12 string dispatcher cases and 81 numeric formatter/alignment cases. These
execute actual game machine code with synthetic BIOS metrics; texture wait,
polygon submission and integer division use explicit stubs. Tests cover mixed
CP932/Latin, punctuation, newline, `@x`/`@r` positioning, negative numbers,
separators, decimal rounding, three alignment choices and stack preservation.
All other executable bytes are checked unchanged. This is code-level evidence,
not an emulator or hardware compatibility guarantee.

The separate Retro Trans Tools `VALIDATION.json` proves the patch reproduces
the entire target track. It is a binary integrity check, not a gameplay test.
