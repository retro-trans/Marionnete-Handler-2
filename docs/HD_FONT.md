# Built-in higher-resolution font — 0.1.5

The user's chosen approach is a font in the game patch, with no Flycast texture
replacement. The cumulative English test image keeps all 793 translations.

The large cached font now uses a 1024×1024 atlas instead of 512×512, with
40-pixel cells and 38-pixel glyph sampling instead of 20-pixel cells and
19-pixel sampling. The renderer still displays a 19-pixel quad and uses the
same normalized texture coordinates. Bearings and advances are converted back
to display pixels. Editable-name slots use the enlarged atlas's bottom row.

This keeps the original BIOS bitmap typeface. Its source glyphs are 24×24;
sampling into the larger atlas preserves more source detail than the previous
reduction to 19×19. It does not introduce a vector typeface or new detail beyond
the BIOS source. The small 12-pixel ASCII font is unchanged. Wide blank spaces
and the pause menu's overflowing Fast-Forward Playback label require separate
layout changes; this patch does not claim to fix them.

The persistent atlas uses a new 2 MiB heap allocation. The upload buffer and
VRAM texture each grow from 512 KiB to 2 MiB. Allocation failure leaves the
original undersized buffer untouched and returns from initialization. Actual
heap/VRAM availability during gameplay and performance need Flycast testing.
This is an experimental test build, not a verified gameplay release.

The original disc and earlier builds remain available. Build with
`tools/build_hd_font.py --build`; running without flags is a read-only plan.
The builder checks source bytes, executable size, placement in proven free
translation-bank fragments, native font initialization, clearing, all 613
cached coordinates, sampled glyph bounds, editable-name bounds and failure
handling. It also runs the existing validation for all 793 messages, verifies
the disc sectors and creates ordinary GDI/CUE files. Platform allocation,
upload and BIOS bitmap inputs are simulated in the limited SH-4 harness.

Load `work/output/english-0.1.5/Marionette Handler 2 English 0.1.5.gdi` in
Flycast to compare the same pause menu with 0.1.4. No texture pack, texture dump
or custom-texture setting is required. Flycast's existing configuration is not
modified. The Retro Trans Tools xdelta package applies to original Track 17,
as with previous cumulative releases.
