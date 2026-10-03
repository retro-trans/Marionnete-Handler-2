# Settings and Clock captions — 0.1.16

The new screenshots show Display Position crossing the Settings button edge
and Wall Clock Design reaching the Clock option value. Radar and armor still
show older long labels; their compact templates were included in 0.1.15 and
are retained here.

Settings uses the native descriptor at executable file offset 0x8c524: seven
entries, 190-pixel width, 22-pixel row height, and pointer table at 0x12e9d0.
Clock uses offset 0x8c7cc: three entries, 186-pixel width, 22-pixel row height,
and pointer table at 0x12ec20. Geometry and value columns remain unchanged.
The native descriptor consists of count, width, height, depth and table pointer.

The display aliases are Position, MARCS Bar, Wall Clock and Clock Style.
The full reviewed English messages remain in the batch files. The versioned
policy is work/translation/en/settings_layout_0.1.16.json. Each shortened
caption occupies its existing compiled slot and the remaining bytes are NUL
padding. Native menu table pointers still select the same slot.

Validation draws all ten captions through the game's renderer with the Bizin
font cache, includes a 16-pixel text inset and checks complete glyph quads.
It also verifies all eleven Parts Change source pointers resolve to compact
stat templates, including radar and armor. The full build runs startup,
793-message, font, shop/editor, equipment and disc checks. User reference
screenshots and native menu dimensions are in work/ui/settings-layout-0.1.16.json.

Test from a fresh boot of work/output/english-0.1.16/Marionette Handler 2 English
0.1.16.gdi; older emulator states restore older text/code. Normal in-game saves
can be used. The cumulative Retro Trans Tools package is work/output/release-0.1.16.
Flycast visual confirmation remains pending.
