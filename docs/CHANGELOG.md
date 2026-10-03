# Change log

## 0.1.14 — program editor help layout — 2026-10-03

- Wrap all 144 distinct editor and chip-palette help messages to 320 pixels,
  using the embedded Bizin Gothic Bold advances and six-pixel spaces.
  Preserve all words, punctuation and compiled text lengths; include the
  enemy-range and Call examples from the user's screenshots.
- Enlarge the native tooltip from 340 x 58 to 340 x 126 pixels. Clamp its
  position within the screen and update the existing cursor-avoidance height.
  Resize an already open tooltip as well as newly created windows.
- Retain all 793 translations, all five shop-category fixes, account labels,
  native variable-width rendering and the lowercase t fix.
- Validate every editor/palette table selection, edge positions, native
  background geometry, disc integrity and the Retro Trans Tools package.
  A fresh Flycast visual check remains pending.

## 0.1.13 — descriptions across all shop categories — 2026-10-03

- Extend the 0.1.12 help background to all five shop categories: Marionette
  Units, Modification Parts, Weapons / Options, Maintenance Supplies and
  Used Parts. Follow the existing shop-window position, fade and draw depth.
- Read coverage from the game's native descriptor table: 24 selections refer
  to 23 distinct descriptions. Wrap all 23, including Option from the user's
  screenshot, within the same 300-pixel advance limit. Preserve every word,
  punctuation mark, paragraph break and original storage length.
- Verify every category selection through the actual shop caller, including
  its description pointer, font setup, drawing bounds and three fade levels.
  Retain the complete translation, Bizin font, six-pixel spaces and prior fixes.
- Validate the rebuilt disc and cumulative Retro Trans Tools package. Fresh
  Flycast visual checks of the new category coverage remain pending.

## 0.1.12 — shop description layout and spacing — 2026-10-03

- Wrap all eleven English parts descriptions to a 300-pixel advance limit,
  preserving every word, punctuation mark and original storage length.
- Replace the 20-pixel ASCII-space fallback with six pixels in cached font
  drawing and measurement. Keep Bizin Gothic Bold and the lowercase t fix.
- Add a taller native background to the parts help overlay, following its
  existing fade and depth. Verify the actual shop caller and all text bounds.
- Correct the separately missed fixed cached mode 3 and scrolling caller to
  use the proportional renderer. The shop caller itself already used mode 1;
  wide spaces, similar Bizin letter widths and old wrapping caused its issue.
- Retain all 793 translations and the four shop/account labels. Verify native
  rendering, original disc integrity and a cumulative Retro Trans Tools package.
  A fresh Flycast visual check remains pending.

## 0.1.11 — shop and account labels — 2026-10-03

- Translate the four labels in the user's screenshots: Buy, Sell, Balance
  (current account balance), and Please wait. These are additional to the
  original 793 reviewed records; two were baked into artwork and two were in
  a separate account string pool.
- Render Buy and Sell with Bizin Gothic Bold inside the original SHOP_00.PVR
  atlas slots. Preserve its ARGB4444 format, transparency, file length, header
  and every pixel outside those two rectangles. No emulator texture pack.
- Store complete account labels in a verified free text bank and retarget the
  two native relative-address literals. Center Balance and place Please wait.
  within the original card. Preserve money rendering and other account states.
- Retain all 793 English records, VWF, embedded Bizin Bold and the corrected
  lowercase t. Verify native account callers, glyph advances, raw disc integrity
  and the cumulative two-track Retro Trans Tools package. Flycast visual checks
  remain pending after a fresh boot.

## 0.1.10 — improve lowercase t — 2026-10-03

- The user's MARCS menu screenshot shows the Bizin bold font loading, and
  identifies lowercase t for refinement. Correct its small-size bitmap with a
  straight stem, smoother lower hook and an ascender two atlas pixels taller.
- Apply the correction to both cached fullwidth-mapped t and editable ASCII t.
  Exactly two glyph records change; every other bitmap, executable byte,
  character bearing and advance remains identical to 0.1.9. The upstream TTF
  is unchanged. Font-source notices remain included in the disc and patch package.
- Add a comparison rendered through the native generator in Marionette,
  Settings and Log Out. Keep all 793 translations and the corrected disc loader.
  Validate the font asset, native rendering, VQ compression, raw disc and
  two-track Retro Trans Tools package. The revised t still needs a Flycast check.

## 0.1.9 — fix Bizin font loading — 2026-10-03

- The user's actual 0.1.8 screenshot and Flycast state confirmed that Bizin
  records never loaded; the valid compressed texture still contained BIOS ink.
  The filename loader passed a full path to a basename lookup in the current
  GDFS directory. Earlier checks simulated that API and missed this failure.
- Open the font's fixed disc extent with the native GDFS sector-open dispatcher,
  then initialize the game's stream state and use its existing reader/close.
  Loading now works independently of the current directory. Align the font
  buffer to 32 bytes for the native reader's DMA path.
- Execute the real GDFS dispatcher, handle allocation, file-size query, stream
  reader and close against the user's captured runtime structures. Simulate only
  physical sector transfer, memory copying and integer division at their leaf
  boundaries; verify every loaded asset byte and handle release.
- Retain Bizin Gothic Bold, all 793 translations, the compact VQ atlas and the
  two-track Retro Trans Tools format. Keep 0.1.8 as evidence of the loader defect.
  The corrected build still needs a fresh Flycast boot and visual confirmation.

## 0.1.8 — embedded Bizin Gothic Bold — 2026-10-02

- Replaced the large BIOS typeface with the user's selected Bizin Gothic Bold
  v0.0.4, covering all 613 cached glyphs and 95 editable ASCII characters.
  Preserved the original TTF, provenance hashes and upstream license notices.
- Added an on-disc ENFONT.BIN asset and a native loader using the game's file
  API. Font records use the unused tail of the original static atlas; missing
  assets and unsupported records retain BIOS fallback. No texture replacement.
- Retained the 1024×1024 atlas, compact VQ texture, proportional spacing and
  all 793 English translations. The small ASCII font and artwork are unchanged.
- Verified every native glyph bitmap and cached metric, loader failure paths,
  exact compression of the generated atlas and all translated message draws.
  Added a native-output comparison against the previous BIOS typeface.
- Added the font to guarded unused ISO space, preserving original file entries.
  The cumulative Retro Trans Tools package applies to BOTH Track 3 and Track 17.
  Actual Flycast startup and gameplay still need confirmation after a fresh boot.

## 0.1.7 — continuous higher-resolution font strokes

- Replaced the BIOS glyph scaler's forward pixel plotting with inverse
  sampling: every pixel in each 38×38 cached or 42×42 editable glyph is now
  written. The previous routine left empty rows when enlarged above the
  source bitmap size, making menu labels appear thin and dotted.
- Retained the original BIOS typeface, displayed size, proportional metrics,
  1024×1024 atlas, native VQ compression and all 793 English translations.
  Glyphs use solid bitmap ink; Flycast's texture filtering controls smoothing.
- Removed the obsolete pixel trampoline and generator code-pointer mutation.
  The new generator reads the atlas pointer from its data global.
- Verified every output pixel against the source bitmap for cached and
  editable glyphs, cache edge placement, ink clearing on regeneration and
  volatile-register clobbering by native integer helpers. Preserved encoder,
  translation, raw-disc and Retro Trans Tools checks.
- Added a comparison rendered through both native generators using the local
  BIOS Latin font, and recorded the user's thin-font screenshot. Flycast
  appearance and gameplay still need visual confirmation after a fresh boot.

## 0.1.6 — compressed higher-resolution font — 2026-10-01

- Investigated the user's blank top menu using their Flycast save state.
  The 0.1.5 atlas contained ink, but its 2 MiB texture failed initialization:
  status `0x60000`, zero hardware size/address words. Later uploads went to
  address zero, so 0.1.5 is a known broken build and should not be used.
- Added a native ARGB4444 VQ encoder for the 1024×1024 atlas. It needs 264,192
  VRAM bytes, less than the original 524,288-byte font. Retained 38-pixel glyph
  sampling, the displayed size, all 793 translations and ordinary GDI/CUE files.
- Reused the original atlas as compression scratch, flushed the encoded upload
  buffer and doubled the glyph metric seed extents along with the sampling.
- Added full native encoder checks for all 256 codebook entries and all 262,144
  blocks, plus an exact pixel round trip of the actual captured BIOS atlas.
  Its transparent/D/F alpha pixels survive unchanged. The unused C alpha level
  rounds to D if a future glyph produces it. Native texture descriptors are
  executed in the harness instead of simulated.
- The corrected disc and Retro Trans Tools package still need a fresh Flycast
  boot and visual confirmation; the saved 0.1.5 state contains the broken code.

## 0.1.5 — experimental built-in higher-resolution font — 2026-10-01

- Enlarged the cached font atlas from 512×512 to 1024×1024 and glyph sampling
  from 19 to 38 pixels, retaining the original displayed size and BIOS typeface.
- Added a cleared heap allocation, enlarged upload/VRAM dimensions and native
  bearing/advance conversion. Kept the editable-name slots within the atlas.
- Preserved all 793 English records and earlier builds. No Flycast texture
  replacement, texture dump or emulator configuration change is used.
- Added native allocation/failure, placement and glyph-bound checks alongside
  the existing translation and raw-disc validation. Added an ordinary test
  image and Retro Trans Tools package.
- Actual Flycast appearance, gameplay memory availability and speed remain
  unverified. Small-font resolution and pause-menu text overflow are unchanged.

## 0.1.4 — all 793 inventoried game messages — 2026-10-01

- Added the remaining 633 English records and independent meaning reviews,
  completing all 793 inventoried game records. Browser/network and artwork text
  remain outside this scope. Expanded the glossary to 45 terms.
- Preserved controls, line counts, full titles and explicit uncertainty notes.
  Corrected comparative/ongoing-action meanings and live Yes/No/step spacing.
- Repacked complete strings across shared storage, retargeted 625 menu pointers
  and added 137 exact-address mappings for relative/static supplemental labels.
  Preserved executable size, native records and numeric fields.
- Added lookup to dispatch, width measurement and the independent aligned
  renderer. Six copied tournament-name handles retain full titles beyond their
  original 32-byte fields. Corrected cached square-bracket conversion.
- Validated actual startup clearing, all 793 native message draws, 137 mappings,
  six copied records, 233 width measurements, 56 aligned-render equivalences and
  14 numeric compositions using the limited SH-4 harness.
- Verified 31 changed raw sectors, EDC/ECC, unchanged bytes elsewhere and all
  17 GDI references. Added the cumulative Retro Trans Tools 0.1.4 release.
- Emulator/hardware playtesting, real BIOS ink metrics and actual screen fit
  remain unverified; source/context and display-layout flags are retained.

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
