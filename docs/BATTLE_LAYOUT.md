# Battle layouts — 0.1.17

The supplied screenshots show enemy help crossing its background, Fast-Forward
Playback extending past its pause button, Yes/No beyond the confirmation edge,
and TotalPerformance underneath the Equipment header.

All four enemy descriptions (rows 413–416) retain their complete words, with
new line breaks measured using the embedded Bizin font. The help window becomes
300 x 132, with a 268-pixel line limit, and stays within x=8..332, y=52..340.
The original native caller at file 0x19b78 still chooses the description from
its own table and draws it at the same inset. A helper at 0x19bc8 updates the
current/target dimensions, including an already open window.

All six pause captions (229–234) fit the four native 142-pixel menu variants:
Resume, Speed Up, Skip, End Battle, Photo Mode, Normal. Normal restores ordinary
playback speed. The reviewed full translations remain in the batch files.

The return-to-MARCS prompt (98) becomes "Stop battle and return / to MARCS?".
The shared native choice prefix at 0x12de38 previously contained a newline and
17 Japanese full-width spaces. It now uses a newline and @x150, preserving the
native Yes/No drawing, colors and input handling. Yes and the existing three
leading spaces before No remain intact. This removes the visible blank-glyph
artifacts and puts the choices within the dialog.

Detailed stats retain all thirteen original English labels and values. Their
native height literal at 0x4373c changes from 188 to 202; Equipment's height at
0x43c64 changes from 78 to 92. A helper at 0x43654 keeps an open Equipment panel
at least four pixels below expanded stats, preserving a larger existing gap.
If needed it limits the stats top to 182 so the default stacked panels remain
inside the 480-pixel screen. Collapsed stats paths remain unchanged.

Validation executes all four enemy-help selections at normal and screen-edge
positions, draws the native background, checks all six menu captions, exercises
three Yes/No selection states, and executes the real stats label and Equipment
callers at three panel positions. The small-font drawing stub captures native
coordinates with its 11-pixel glyph extent; platform submission remains stubbed.
The full build also verifies all 793 messages, font pixels, startup survival,
prior shop/editor/equipment/Settings fixes and disc read-back. This is native
code-level validation; Flycast visual confirmation remains pending.

The display policy is work/translation/en/battle_layout_0.1.17.json; screenshot
references and native dimensions are work/ui/battle-layout-0.1.17.json. Fresh-boot
work/output/english-0.1.17/Marionette Handler 2 English 0.1.17.gdi. The cumulative
Retro Trans Tools package is work/output/release-0.1.17.
