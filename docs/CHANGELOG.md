# Change log

## 0.1.3 — second English translation batch — 2026-10-01

- Added 80 reviewed menu/system messages (rows 81–160), bringing the cumulative
  translation to 160 of 793 inventoried game entries (20.2%). Examined eight
  neighboring records for context and expanded the glossary to 33 terms.
- Confirmed native price, timer, alarm, card-insertion and purchased-save
  composition. Corrected stop-confirmation direction and timer agreement;
  retained explicit source-omission and mixed-language runtime-label flags.
- Repacked both complete batches into their 6,999-byte shared bank using
  6,062 bytes, retargeting 164 pointers, including both shared insertion aliases.
- Extended native validation to 320 message draws, ten composed card messages,
  three price confirmations and the three existing block-count warnings.
  Preserved exact 0.1.2 executable reproduction and existing-track verification.
- Added cumulative build/version selection, source-bound review evidence,
  full-track/descriptor checks and the Retro Trans Tools 0.1.3 patch release.
- Verified ten modified raw sectors, valid EDC/ECC, unchanged bytes elsewhere
  and all 17 GDI references. Original disc tracks remain untouched.
- Actual BIOS font metrics, screen fit and emulator/hardware playtesting remain
  unverified. Remaining port labels and timer units are queued for later slices.

## 0.1.2 — first English translation batch — 2026-10-01

- Translated and meaning-reviewed the first 80 system/shop UI messages, with
  four adjacent records examined for context. Added a 26-term English glossary.
- Repacked the complete English strings into their shared UI bank and updated
  83 verified pointers. Individual source slots do not limit these translations.
- Retained VWF, newline/control behavior, live block counts, executable size
  and all untranslated records. Confirmed the free-block warning shows a deficit.
- Added 160 native string-dispatch checks and three composed numeric-warning
  checks, actual default font-cache loading with simulated BIOS ink metrics,
  original-hash and terminology guards, full-track/descriptor verification,
  and Retro Trans Tools packaging for the English test release.
- Recorded display-length measurements and remaining context/layout flags.
  Actual cached-font fit and emulator/hardware playtesting remain unverified.

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
