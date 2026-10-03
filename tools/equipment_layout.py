"""Compact native equipment labels for the original stat/button columns."""
import hashlib
import json
import re
import struct

from build_english import prepare_native_cache
from build_vwf import BASE
from full_english import batches, merged
from inspect_disc_text import ROOT
from validate_vwf import CPU

VERSION = '0.1.15'
POLICY = ROOT / 'work/translation/en/equipment_layout_0.1.15.json'
STAT_ROWS = [740] + list(range(767, 782))
MENU_ROWS = list(range(208, 217))
TYPE_ROWS = list(range(762, 767))


def plan(original, program, report):
    result = bytearray(program)
    _, texts, _ = batches()
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    assert policy['version'] == VERSION
    entries = policy['translations']
    assert sorted(e['row'] for e in entries) == sorted(STAT_ROWS + MENU_ROWS + TYPE_ROWS)
    metrics = {r['character']: r['advance'] for r in report['font_asset']['latin_metrics']}
    metrics[' '] = report['space_advance_px']
    changes = list(report['changed_regions'])
    for entry in entries:
        row, text = entry['row'], entry['target']
        source = texts[row - 1]
        assert source == entry['full_translation']
        assert re.findall(r'@[a-zA-Z]\d{3}', source) == re.findall(r'@[a-zA-Z]\d{3}', text)
        assert source.count('\n') == text.count('\n')
        assert len(text.encode('ascii')) <= len(source.encode('ascii'))
        binding = report['bindings'][row - 1]
        at = binding['target_file_offset']
        assert result[at:at + len(source) + 1] == source.encode('ascii') + b'\0'
        result[at:at + len(source) + 1] = text.encode('ascii').ljust(len(source) + 1, b'\0')
        binding.update(target_bytes=len(text), target_sha256=hashlib.sha256(text.encode()).hexdigest(),
                       review_note=entry['note'])
        report['layout_overrides'][str(row)] = text
        changes.append((at, at + len(source) + 1))
        lines = re.sub(r'@[a-zA-Z]\d{3}', '', text).split('\n')
        entry['line_advances'] = [sum(metrics[c] for c in line) for line in lines]
        assert max(entry['line_advances']) <= (98 if row in STAT_ROWS else 132 if row in MENU_ROWS else 64)
    assert struct.unpack_from('<If', original, 0x8c614) == (9, 152.0)
    report.update(version=VERSION, equipment_layout={'entries': entries, 'stat_rows': STAT_ROWS,
                  'menu_rows': MENU_ROWS, 'type_rows': TYPE_ROWS, 'menu_button_width': 152,
                  'stat_label_max_advance': 98, 'type_max_advance': 64,
                  'native_value_field_widths': [180, 80], 'native_controls_preserved': True},
                  changed_regions=merged(changes), target_program_sha256=hashlib.sha256(result).hexdigest())
    assert len(result) == len(program)
    return bytes(result)


def validate(program, report, metrics):
    template, _, codes, _ = prepare_native_cache(program)
    for i, code in enumerate(codes):
        bearing, advance = metrics[code]
        template.write(0x8c34dbb4 + i, bearing, 1)
        template.write(0x8c34de28 + i, advance, 1)

    def setup():
        cpu = CPU(program)
        cpu.mem[0x34d6d0:0x34e0c0] = template.mem[0x34d6d0:0x34e0c0]
        cpu.write(0x8c13d75c, 1)
        cpu.write_float(0x8c13d758, 1)
        cpu.write_float(0x8c34e0c0, 0)
        cpu.write_float(0x8c34e0c4, 0)
        cpu.write_float(0x8c34e0c8, 0)
        cpu.f[4] = 100
        return cpu

    def capture(cpu, vertices):
        def submit():
            vertices.extend((cpu.read_float(cpu.r[4] + i * 24),
                             cpu.read_float(cpu.r[4] + i * 24 + 4)) for i in range(4))
            cpu.submit()
        cpu.stubs[0x8c1731a4] = submit

    def bounds(vertices):
        return [min(x for x, y in vertices), min(y for x, y in vertices),
                max(x for x, y in vertices), max(y for x, y in vertices)]

    checks = []
    for entry in report['equipment_layout']['entries']:
        row = entry['row']
        cpu, vertices = setup(), []
        capture(cpu, vertices)
        binding = report['bindings'][row - 1]
        if row in TYPE_ROWS:
            cpu.r[4] = BASE + binding['source_file_offset']
            cpu.f[4] = 80
            cpu.run(BASE + 0x6460, limit=3000000)
            box = bounds(vertices)
            assert 12 <= box[0] <= box[2] <= 90, (row, box)
        else:
            if row in MENU_ROWS:
                cpu.write_float(0x8c34e0c0, 16)
                cpu.write_float(0x8c34e0c4, 16)
            cpu.r[4] = (struct.unpack_from('<I', program, binding['pointer_locations'][0])[0]
                        if row in MENU_ROWS else BASE + binding['source_file_offset'])
            cpu.run(BASE + 0x6090, limit=3000000)
            box = bounds(vertices)
            assert box[2] <= (152 if row in MENU_ROWS else 107), (row, box)
        assert cpu.r[15] == 0x8cf00000
        checks.append({'row': row, 'quad_bounds': box})
    # Worst five-digit number and an ordinary three-digit value use the same
    # native right-aligned formatter as these equipment screens.
    numeric = []
    for number in (0, 130, 250, 1000, 65535):
        cpu, vertices = setup(), []
        capture(cpu, vertices)
        cpu.r[4], cpu.f[4] = number, 180
        cpu.run(BASE + 0x5c1c)
        box = bounds(vertices)
        assert box[0] > max(c['quad_bounds'][2] for c in checks if c['row'] in STAT_ROWS), (number, box)
        numeric.append({'value': number, 'quad_bounds': box})
    # Execute the actual current/selected main-weapon callers. Keep the real
    # template, name, newline-prefix, string alignment and numeric calls.
    popup_cases = []
    for first in range(5):
        for second in range(5):
            cpu, vertices = setup(), []
            capture(cpu, vertices)
            cpu.f[13:16] = [100, 80, 172]
            current = 0x8c2c6ac0
            cpu.mem[current - 0x8c000000 + 0x364:current - 0x8c000000 + 0x36d] = b'Normal-S\0'
            for offset, value in ((0x37c, first), (0x380, 13), (0x388, 96), (0x38c, 20)):
                cpu.write(current + offset, value)
            cpu.run(BASE + 0x3d338, stop=BASE + 0x3d3d4, limit=3000000)
            current_vertices = list(vertices)
            # The selected item's name and byte-sized model statistics.
            cpu.r[13] = 0
            selected = 0x8c0a10bc
            cpu.mem[selected - 0x8c000000 + 4:selected - 0x8c000000 + 12] = b'Laser-S\0'
            for offset, value in ((25, second), (26, 15), (28, 78), (29, 20)):
                cpu.write(selected + offset, value, 1)
            cpu.write_float(cpu.r[15], 80)
            cpu.write_float(cpu.r[15] + 4, 348)
            cpu.f[12] = 100
            vertices.clear()
            cpu.run(BASE + 0x3d444, stop=BASE + 0x3d4ec, limit=3000000)
            assert cpu.r[15] == 0x8cf00000
            # Compare type-value ink/quad bounds at y=102, excluding labels.
            left_type = [v for v in current_vertices if 102 <= v[1] <= 121 and v[0] >= 292]
            right_type = [v for v in vertices if 102 <= v[1] <= 121]
            assert left_type and right_type
            assert max(x for x, y in left_type) < min(x for x, y in right_type), (first, second)
            popup_cases.append({'current_type': first, 'selected_type': second,
                                'current_right': max(x for x, y in left_type),
                                'selected_left': min(x for x, y in right_type)})
    print('Equipment: 16 stat templates, 9 maintenance buttons, 5 types and 25 native comparisons fit.', flush=True)
    return {'labels': checks, 'numeric_value_cases': numeric, 'native_main_weapon_comparisons': popup_cases,
            'all_template_controls_retained': True, 'actual_Flycast_playtest': False}
