# Change log

## 0.1.1 — VWF test patch — 2026-10-01

- Enabled the existing proportional cached-font renderer for font mode 4 and
  integer/decimal readouts. Right alignment now measures actual glyph advances.
- Replaced the ASCII converter with an equivalent compact lookup table,
  preserved its legacy icon mapping, and added braces, pipe and tilde.
- Added configurable small Latin metrics, a checked SH-4 patch encoder,
  MODE1 EDC/ECC regeneration, and a limited machine-code validation harness.
- Added local BIN/CUE/GDI test-build generation and Retro Trans Tools release
  packaging with full-track xdelta round-trip verification and checksums.
- Changes occupy existing executable space and four raw sectors in Track 17;
  original tracks are preserved. No translated script is included.
- Code-level validation covers glyph widths, control positioning, mixed text
  and numeric alignment. Emulator/hardware playtesting remains outstanding.

## 0.1.0 — discovery tools and assessment — 2026-10-01

- Added a read-only BIN/CUE disc inspection tool and a reproducible,
  source-free text inventory.
- Located 793 Japanese game text entries (732 distinct strings) and 773
  network/browser messages (766 distinct strings).
- Documented extraction methods, excluded binary false positives, and
  identified image-based text and additional browser content as uncounted.
- Original disc files remain unchanged. This is an assessment/tool version,
  not a playable release; Retro Trans Tools compatibility is not yet tested.
