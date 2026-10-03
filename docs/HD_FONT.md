# Embedded Bizin Gothic Bold — 0.1.10

The game now uses [Bizin Gothic Bold v0.0.4](https://github.com/yuru7/bizin-gothic)
for the large cached font and editable-name glyphs. The original typeface was
the Dreamcast BIOS bitmap font. Its strokes remained thin after the missing-row
sampling bug was corrected in 0.1.7. Bizin Gothic combines Inconsolata Latin
characters with BIZ UD Gothic Japanese characters; this build uses the upstream
Bold TTF, preserved unchanged with its source hashes and OFL notices.

0.1.10 corrects the lowercase t's small-size bitmap: its stem is straight,
the lower hook is smoother and the ascender extends two atlas pixels farther
up. Both cached and editable t are updated. All other glyphs, the executable,
bearings and advances are unchanged from 0.1.9. The source TTF remains intact;
the adjustment applies only to the derived game bitmaps. The user's cropped
MARCS menu screenshot after testing 0.1.9 shows the Bizin bold labels loading.
The new t still needs visual confirmation in Flycast.

The game loads `/ENFONT.BIN` from its fixed patched-disc extent. It contains 613 cached glyph
records, 95 editable ASCII records, and the font license notices. All 708
characters are covered by the selected font. Latin glyphs are rasterized at 44
pixels and the other characters at 35 pixels, fitted inside 38×38 cells. The
native generator reads these bitmaps and computes each cached character's
bearing and advance. Missing assets, invalid headers, and unsupported records
fall back to the BIOS font. The small 12-pixel ASCII font and text baked into
artwork retain their original appearance.

The atlas remains 1024×1024, with 40-pixel cached cells, 38-pixel cached glyphs,
and 42-pixel editable glyphs. The displayed cached quad is still 19 pixels.
Binary rasterization gives solid strokes; Flycast's filtering affects smoothing
at the displayed size. This is a higher-resolution bitmap font inside the game,
not a vector renderer or an emulator texture replacement.

The persistent atlas and temporary upload buffer each use 2 MiB of RAM. Native
ARGB4444 VQ compression keeps the video-memory texture at 264,192 bytes. The
font records occupy 135,952 bytes in the unused tail of the original static
atlas, beyond the compression scratch space, without another heap allocation.
The loader opens FAD 549150 (LBA 549000) through the native GDFS sector-open
dispatcher, initializes the stream globals and reads the records once through
the game's original reader. Its buffer is 32-byte aligned for DMA. It works
independently of the current GDFS directory.

The user's 0.1.8 screenshot and saved state showed that its font records never
loaded: that loader handed a full path to a basename-only lookup API. The
compressed texture itself was valid but contained fallback BIOS glyphs. The
earlier file-I/O simulation missed that integration defect. 0.1.9 corrects it.

The ISO root directory gains one file entry in Track 3. Its data occupies
guarded all-zero sectors at the end of Track 17. All original ISO entries keep
their locations and sizes. The cumulative executable keeps all 793 English
translations. Consequently, the Retro Trans Tools package has TWO patches:
apply both Track 3 and Track 17 to the original Japanese raw tracks.

Build with `python tools/build_hd_font.py --build`; no flags produces a read-only
plan, and `--validate` executes the checks without writing a disc. Existing
output folders are refused. The limited SH-4 harness checks the loader's success,
reuse and failure paths; all 708 record lookups and rendered bitmaps; all 613
cached metrics; BIOS fallback; font initialization and allocation failure;
editable bounds; and the complete native VQ encoder. The generated Bizin atlas
must survive compression with every pixel identical. All 793 messages, numeric
compositions and aligned rendering are checked with the actual Bizin metrics.
Platform file I/O, allocation, uploads and BIOS services are simulated.

For stronger loader validation, add `--loader-state <0.1.8.state>` or run
`python tools/validate_font_loader.py <0.1.8.state> --report`. This executes the
actual GDFS dispatcher, handle allocation, size query, stream reader and close
against the user's captured directory/device/handle structures. Only the
physical sector transfer and leaf copy/division helpers are simulated. The
check proves that all 135,952 bytes arrive intact, the native close releases the
handle, the aligned bulk destination is correct and a repeated load reads
nothing. The report saves no game RAM or Japanese scripts.

The disc verifier reads the new font through its ISO entry, compares the patched
executable, verifies every changed sector's EDC/ECC, proves other sectors are
unchanged, and checks all 17 GDI track references. The release SDK reconstructs
both complete changed tracks and compares their hashes.

`python tools/preview_hd_font.py --bios <dc_boot.bin> --write` saves a comparison
in `work/ui/font-BIOS-vs-Bizin-Gothic-Bold-0.1.8.png`. It uses actual native glyph
output and is labeled as a preview, rather than an in-game screenshot.

`python tools/preview_t_font.py --bios <dc_boot.bin> --write` compares the old
and corrected t through the native generator, including the three menu labels
from the user's screenshot. It verifies that only the two t records change
and that the executable and word advances remain identical. The labeled output
is `work/ui/font-t-0.1.9-vs-0.1.10.png`.

Open `work/output/english-0.1.10/Marionette Handler 2 English 0.1.10.gdi` in Flycast
and boot from scratch. An older save state restores the older renderer and font.
No texture dump, custom texture pack or Flycast setting change is needed.
Flycast appearance, file loading during startup, gameplay memory availability
and screen fit still need a real playtest. The known pause-menu label overflow
and the native wide blank spaces are separate layout issues.

Earlier builds remain available. 0.1.5 is known broken: the uncompressed 2 MiB
VRAM texture failed initialization, leaving blank menus. 0.1.6 introduced VQ
compression; 0.1.7 fixed empty rows in the enlarged BIOS font.
