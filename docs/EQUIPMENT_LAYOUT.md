# Equipment statistics and maintenance - 0.1.15

The screenshots show three related problems: English stat labels reach into
right-aligned values, long equipment types overlap the comparison column, and
maintenance captions extend past their native buttons. Changing the glyph
shape alone cannot resolve these fixed column limits.

This build applies compact display aliases to all sixteen stat templates,
five equipment types and nine maintenance captions. The full English targets
remain in the reviewed batch files. The versioned display policy is
work/translation/en/equipment_layout_0.1.15.json. Every original positioning
control and line break is preserved. The aliases fit in their existing slots,
so neither native layout code nor the embedded Bizin font changes in 0.1.15.
The prior shop and editor help patches remain included.

Stat labels have at most 98 pixels of advance. The original value fields stay
180 pixels wide, with 80-pixel fields in comparisons. Maintenance buttons stay
152 pixels wide; the validation includes a 16-pixel text inset and complete
native glyph quads. Names of individual models/items stay unchanged.

Some display aliases:

| Full translation | Compact display |
| --- | --- |
| Attack Power / Ammo Count | Attack / Ammo |
| Power Consumption / Energy Consumption | Pwr Use / E.Use |
| Movement / Attack / Enemy Search / Branch Processing | Move Pr / Atk Pr. / Scan Pr. / Br. Pr. |
| Electrical Capacity / Combustion Efficiency | ElecCap / FuelEff |
| Rotational Speed / Rebound Force / Damping Force | Spin / Rebound / Damping |
| Enemy Search Angle / Enemy Search Range | ScanArc / ScanRng |
| Mark Angle / Mark Range | MarkArc / MarkRng |
| Impact / Heat / Electromagnetic Resistance | Hit Res / HeatRes / EM Res |
| Normal | Norm. |
| Light/Heat | Lt/Ht |
| Electromagnetic | EM |
| Electrical/Thermal | E/Ht |
| Super-electromagnetic | S-EM |
| Replace Parts / Clock Adjustment | Swap Parts / Clock Tune |
| Output Adjustment / Brake Adjustment | Output Tune / Brake Tune |
| Reinforcement / Weight Reduction / Maintenance | Reinforce / Lighten / Service |

Clock Tune means CPU clock tuning, distinct from the wall clock. Service
remains distinct from Repair. Scan retains the enemy-search meaning. Pr.
means Processing; the CPU template retains all four processing categories.
These are display abbreviations, not removals of statistics or help content.

Native checks draw every affected label using the embedded font, test ordinary
and five-digit numeric values, and execute all 25 current/selected type pairs
through the game's main-weapon comparison callers. They exercise real name,
newline, template, right-aligned string and numeric drawing. Full startup,
793-message, font, shop/editor and disc checks also run with the build.
Evidence is in work/ui/english_0.1.15_inventory.json. A fresh Flycast visual
check remains pending; user screenshots are preserved as before references.

Open work/output/english-0.1.15/Marionette Handler 2 English 0.1.15.gdi from a
fresh boot. The cumulative Retro Trans Tools package is in
work/output/release-0.1.15/ and reconstructs patched Track 3 and Track 17 from
the original Japanese raw tracks.
