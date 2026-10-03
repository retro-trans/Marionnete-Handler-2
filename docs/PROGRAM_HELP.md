# Program editor help - 0.1.14

The shared editor help table has 151 slots; the palette uses its final 42
slots. Together these refer to 144 distinct translated messages (rows 417-560),
with duplicate references and four empty placeholders. Coverage comes from the
native pointer tables, including all movement, condition, label, counter and
palette help, rather than only the screenshots.

The existing English translation is reflowed at word boundaries using the
embedded Bizin Gothic Bold advances and six-pixel ASCII spaces. Each line has
at most 320 pixels of advance inside the 340-pixel tooltip. Every word,
punctuation mark and compiled byte length is retained. The longest messages,
Call and Enemy Search Chip, need five lines.

The native window grows from 58 to 126 pixels high. The text starts eight
pixels from the left and twelve from the top, with 22-pixel line spacing.
The editor's window creation, current dimensions, animation target dimensions
and cursor avoidance use the larger size. A small native helper clamps the
window position to x=8..292 and y=52..346 on the 640x480 screen. It also resizes
an already open tooltip. Other callers of the generic window renderer keep
their own dimensions. No emulator texture replacement is required.

The wrapping policy is work/translation/en/program_help_layout_0.1.14.json.
The compiled evidence and native draw checks are recorded in
work/ui/english_0.1.14_inventory.json. Checks execute every populated editor
and palette selection, plus the screenshot examples and longest messages at
screen edges. They verify glyph bounds, the real native window background,
proportional spacing, pointer selection and stack balance. Full font, all 793
messages, startup memory survival and disc-sector checks run with the build.
A fresh Flycast visual check remains pending.

Open work/output/english-0.1.14/Marionette Handler 2 English 0.1.14.gdi
from a fresh boot. Keep the workspace's original tracks alongside it. The
cumulative Retro Trans Tools package is work/output/release-0.1.14/ and patches
both Track 3 and Track 17 in a separate copy of the original Japanese disc.
