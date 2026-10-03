"""Fit native Settings and Clock captions while retaining their value columns."""
import hashlib
import json
import struct

from build_english import prepare_native_cache
from build_vwf import BASE
from full_english import batches, merged
from inspect_disc_text import ROOT
from validate_vwf import CPU

VERSION = '0.1.16'
POLICY = ROOT / 'work/translation/en/settings_layout_0.1.16.json'
GROUPS = [('settings', range(199, 206), 0x8c524, 190),
          ('clock', range(299, 302), 0x8c7cc, 186)]


def plan(original, program, report):
    result = bytearray(program)
    _, texts, _ = batches()
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    assert policy['version'] == VERSION
    entries = policy['translations']
    assert [e['row'] for e in entries] == [row for _, rows, _, _ in GROUPS for row in rows]
    advances = {r['character']: r['advance'] for r in report['font_asset']['latin_metrics']}
    advances[' '] = report['space_advance_px']
    changes = list(report['changed_regions'])
    for name, rows, descriptor, width in GROUPS:
        count, native_width = struct.unpack_from('<If', original, descriptor)
        assert count == len(rows) and native_width == width
        pointer_table = struct.unpack_from('<I', original, descriptor + 16)[0] - BASE
        for row in rows:
            entry = next(e for e in entries if e['row'] == row)
            source, text = texts[row - 1], entry['target']
            assert source == entry['full_translation']
            assert '@' not in source and '\n' not in source
            assert len(text) <= len(source)
            binding = report['bindings'][row - 1]
            assert pointer_table + 4 * (row - rows.start) in binding['pointer_locations']
            at = binding['target_file_offset']
            assert result[at:at + len(source) + 1] == source.encode('ascii') + b'\0'
            if source != text:
                result[at:at + len(source) + 1] = text.encode('ascii').ljust(len(source) + 1, b'\0')
                changes.append((at, at + len(source) + 1))
                report['layout_overrides'][str(row)] = text
                binding.update(target_bytes=len(text), target_sha256=hashlib.sha256(text.encode()).hexdigest(),
                               review_note=entry['note'])
            entry.update(group=name, native_button_width=width,
                         advance=sum(advances[c] for c in text))
            assert entry['advance'] + 20 <= width
    report.update(version=VERSION, settings_layout={'entries': entries, 'native_text_inset': 16,
                  'native_menu_geometry_unchanged': True}, changed_regions=merged(changes),
                  target_program_sha256=hashlib.sha256(result).hexdigest())
    return bytes(result)


def validate(program, report, metrics):
    template, _, codes, _ = prepare_native_cache(program)
    for i, code in enumerate(codes):
        bearing, advance = metrics[code]
        template.write(0x8c34dbb4 + i, bearing, 1)
        template.write(0x8c34de28 + i, advance, 1)
    checks = []
    for entry in report['settings_layout']['entries']:
        cpu, vertices = CPU(program), []
        cpu.mem[0x34d6d0:0x34e0c0] = template.mem[0x34d6d0:0x34e0c0]
        cpu.write(0x8c13d75c, 1)
        cpu.write_float(0x8c13d758, 100)
        cpu.write_float(0x8c34e0c0, 16)
        cpu.write_float(0x8c34e0c4, 16)
        cpu.write_float(0x8c34e0c8, 0)
        def submit():
            vertices.extend((cpu.read_float(cpu.r[4] + i * 24),
                             cpu.read_float(cpu.r[4] + i * 24 + 4)) for i in range(4))
            cpu.submit()
        cpu.stubs[0x8c1731a4] = submit
        binding = report['bindings'][entry['row'] - 1]
        cpu.r[4] = struct.unpack_from('<I', program, binding['pointer_locations'][0])[0]
        cpu.run(BASE + 0x6090, limit=3000000)
        box = [min(x for x,y in vertices), min(y for x,y in vertices),
               max(x for x,y in vertices), max(y for x,y in vertices)]
        assert box[2] <= entry['native_button_width'], (entry['row'], box)
        assert cpu.r[15] == 0x8cf00000
        checks.append({'row': entry['row'], 'quad_bounds': box,
                       'button_width': entry['native_button_width']})
    # These two screenshots also show old radar/armor labels. Verify all eleven
    # parts source pointers still resolve to the cumulative compact templates.
    for row in range(771, 782):
        cpu = CPU(program)
        binding = report['bindings'][row - 1]
        cpu.r[4] = BASE + binding['source_file_offset']
        cpu.run(BASE + 0x7de4)
        assert cpu.r[4] == BASE + binding['target_file_offset']
        text = report['layout_overrides'][str(row)].encode('ascii')
        at = binding['target_file_offset']
        assert program[at:at + len(text) + 1] == text + b'\0'
    print('Settings/Clock: all 10 captions fit; all 11 compact parts templates retained.', flush=True)
    return {'labels': checks, 'compact_parts_templates_verified': 11,
            'actual_Flycast_playtest': False}
