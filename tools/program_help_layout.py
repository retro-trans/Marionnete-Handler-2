"""Wrap all editor/palette help and enlarge the native tooltip window."""
import hashlib
import json
import struct

from build_vwf import BASE, patched_conversion
from build_english import prepare_native_cache
from full_english import batches, merged
from inspect_disc_text import ROOT
from sh4_patch import Assembler
from shop_description_layout import hook, SPACE
from validate_vwf import CPU

VERSION = '0.1.14'
WIDTH, PANEL_WIDTH, HEIGHT = 320, 340, 126
TABLES = [(1, 0x12f1b4, 151), (2, 0x12f368, 42)]
POLICY = ROOT / 'work/translation/en/program_help_layout_0.1.14.json'


def wrap(text, metrics):
    lines, line = [], ''
    for word in text.split():
        assert sum(metrics[c] for c in word) <= WIDTH
        candidate = line + (' ' if line else '') + word
        if sum(metrics[c] for c in candidate) > WIDTH:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    result = '\n'.join(lines)
    assert ' '.join(result.split()) == ' '.join(text.split())
    assert len(result.encode('ascii')) == len(text.encode('ascii'))
    assert len(lines) <= 5
    return result


def coverage(original, report):
    rows = {b['source_file_offset']: b['row'] for b in report['bindings']}
    entries = []
    for kind, table, count in TABLES:
        for index in range(count):
            pointer = struct.unpack_from('<I', original, table + index * 4)[0]
            row = rows.get(pointer - BASE)
            if row is None:
                assert pointer == 0x8c14689f
                assert original[pointer - BASE:pointer - BASE + 7] == b'\x81\x40' * 3 + b'\0'
            entries.append({'kind': kind, 'index': index, 'row': row,
                            'pointer_file_offset': table + index * 4})
    assert sorted({e['row'] for e in entries if e['row']}) == list(range(417, 561))
    return entries


def helper(start):
    a = Assembler(start)
    constants = []

    def number(value, register=0):
        marker = 0x12340000 + len(constants)
        constants.append((marker, float(value)))
        a.load(0, marker)
        a.emit(0xf008 | register << 8)

    # Called by a tail jump at 0x2581c. The original preceding instruction
    # loaded the window index address. Recreate the overwritten record setup.
    a.load(0, 0x8c1a4264)
    a.emit(0x6402)  # mov.l @r0,r4
    a.emit(0xe02c, 0x0407, 0x041a)  # index * 44 -> r4
    a.load(3, 0x8c1a4328)
    a.emit(0x334c)  # r3 = record
    for global_at, low, high, record_offset in (
            (0x8c34f11c, 8, 632 - PANEL_WIDTH, 4),
            (0x8c34f120, 52, 472 - HEIGHT, 8)):
        a.load(1, global_at)
        a.emit(0xf118)  # fr1 = global coordinate
        number(low)
        a.emit(0xf105)
        a.branch(0x8900, 'low_ok_' + str(record_offset))
        a.emit(0xf10c)
        a.label('low_ok_' + str(record_offset))
        number(high)
        a.emit(0xf105)
        a.branch(0x8b00, 'high_ok_' + str(record_offset))
        a.emit(0xf10c)
        a.label('high_ok_' + str(record_offset))
        a.emit(0xf11a)  # write clamped global
        a.emit(0x6033, 0x7000 | record_offset, 0xf01a)
    # Set current and target dimensions, including an already open tooltip.
    for offset, value in ((16, PANEL_WIDTH), (20, HEIGHT),
                          (32, PANEL_WIDTH), (36, HEIGHT)):
        number(value, 1)
        a.emit(0x6033, 0x7000 | offset, 0xf01a)
    a.emit(0x7308)
    a.load(0, 0x8c34f120)
    a.load(1, BASE + 0x25838)
    a.emit(0x412b, 0x0009)
    blob = a.finish()
    for marker, value in constants:
        blob = blob.replace(struct.pack('<I', marker), struct.pack('<I', start + len(blob)))
        blob += struct.pack('<f', value)
    return blob


def plan(original, program, report):
    result = bytearray(program)
    changes = list(report['changed_regions'])
    metrics = {r['character']: r['advance'] for r in report['font_asset']['latin_metrics']}
    metrics[' '] = SPACE
    _, texts, _ = batches()
    policy = json.loads(POLICY.read_text())
    approved = {r['row']: r['target'] for r in policy['translations']}
    entries = coverage(original, report)
    layouts = []
    for row in range(417, 561):
        text = wrap(texts[row - 1], metrics)
        assert policy['version'] == VERSION and policy['max_line_advance_px'] == WIDTH
        assert approved[row] == text
        binding = report['bindings'][row - 1]
        at = binding['target_file_offset']
        assert result[at:at + len(text)] == texts[row - 1].encode('ascii')
        result[at:at + len(text)] = text.encode('ascii')
        binding.update(target_sha256=hashlib.sha256(text.encode('ascii')).hexdigest(),
                       line_count=text.count('\n') + 1)
        report['layout_overrides'][str(row)] = text
        changes.append((at, at + len(text)))
        layouts.append({'row': row, 'target': text, 'words_preserved': True,
                        'line_advances': [sum(metrics[c] for c in line) for line in text.split('\n')]})
    fragments = report['allocation']['free_fragments']
    for fragment in fragments:
        start, end = fragment
        start = (start + 3) & ~3
        blob = helper(BASE + start)
        if start + len(blob) <= end:
            break
    else:
        raise ValueError('No verified free fragment for tooltip helper')
    result[start:start + len(blob)] = blob
    fragment[0] = start + len(blob)
    report['allocation']['remaining_fragment_bytes'] = sum(z - a for a, z in fragments)
    hook(result, 0x2581c, BASE + start)
    assert struct.unpack_from('<f', original, 0x25504)[0] == 58
    struct.pack_into('<f', result, 0x25504, HEIGHT)
    # The editor's existing cursor avoidance tests use the tooltip's height.
    assert struct.unpack_from('<f', original, 0x25710)[0] == 32
    struct.pack_into('<f', result, 0x25710, HEIGHT - 26)
    changes += [(start, start + len(blob)), (0x2581c, 0x25828),
                (0x25504, 0x25508), (0x25710, 0x25714)]
    report.update(version=VERSION, changed_regions=merged(changes),
                  target_program_sha256=hashlib.sha256(result).hexdigest(),
                  program_help_layout={'descriptions': layouts, 'entries': entries,
                                       'max_line_advance': WIDTH, 'panel_size': [PANEL_WIDTH, HEIGHT],
                                       'text_inset': [8, 12], 'position_limits': [8, 52, 292, 346],
                                       'helper_offset': start, 'helper_bytes': len(blob),
                                       'native_window_creation_height': HEIGHT})
    assert len(result) == len(program)
    return bytes(result)


def validate(program, report, metrics):
    template, _, codes, _ = prepare_native_cache(program)
    for index, code in enumerate(codes):
        bearing, advance = metrics[code]
        template.write(0x8c34dbb4 + index, bearing, 1)
        template.write(0x8c34de28 + index, advance, 1)
    cases = []
    entries = report['program_help_layout']['entries']
    # Every table slot, both screenshots at screen edges, and pre-fix states.
    inputs = [(e, 240, 274) for e in entries if e['row']]
    inputs += [(next(e for e in entries if e['row'] == row), x, y)
               for row in (504, 507, 532) for x, y in ((-20, 0), (620, 460))]
    for entry, x, y in inputs:
        cpu = CPU(program)
        cpu.mem[0x34d6d0:0x34e0c0] = template.mem[0x34d6d0:0x34e0c0]
        cpu.write_float(0x8c13d758, 1)
        cpu.write(0x8c1a4264, 2)
        record = 0x8c1a4328 + 2 * 44
        cpu.write_float(record + 12, -5)
        cpu.write_float(record + 20, 58)
        cpu.write_float(0x8c34f11c, x)
        cpu.write_float(0x8c34f120, y)
        cpu.r[13:15] = [entry['kind'], entry['index']]
        vertices = []

        def submit():
            vertices.extend((cpu.read_float(cpu.r[4] + i * 24),
                             cpu.read_float(cpu.r[4] + i * 24 + 4)) for i in range(4))
            cpu.submit()

        cpu.stubs[0x8c1731a4] = submit
        cpu.run(BASE + 0x2581a, stop=BASE + 0x258aa, limit=3000000)
        left, top = min(max(x, 8), 292), min(max(y, 52), 346)
        assert cpu.read_float(record + 4) == left
        assert cpu.read_float(record + 8) == top
        for offset, value in ((16, PANEL_WIDTH), (20, HEIGHT), (32, PANEL_WIDTH), (36, HEIGHT)):
            assert cpu.read_float(record + offset) == value
        assert vertices
        bounds = [min(x for x, y in vertices), min(y for x, y in vertices),
                  max(x for x, y in vertices), max(y for x, y in vertices)]
        assert left <= bounds[0] <= bounds[2] <= left + PANEL_WIDTH, (entry, bounds)
        assert top <= bounds[1] <= bounds[3] <= top + HEIGHT, (entry, bounds)
        assert cpu.r[15] == 0x8cf00000
        backgrounds = []

        def rectangle():
            backgrounds.append([cpu.read_float(0x8c1a34e4 + i * 4) for i in range(4)])

        cpu.stubs[BASE + 0x91dc] = rectangle
        cpu.stubs[BASE + 0x93d4] = lambda: None
        cpu.r[4] = 2
        cpu.run(BASE + 0x10a5c)
        assert backgrounds[0] == [left, top + 2, left + PANEL_WIDTH, top + 2 + HEIGHT]
        assert cpu.r[15] == 0x8cf00000
        text = report['layout_overrides'][str(entry['row'])]
        last_width = sum(SPACE if c == ' ' else metrics[patched_conversion(ord(c))][1]
                         for c in text.split('\n')[-1])
        assert cpu.read_float(0x8c34e0c0) == left + 8 + last_width
        assert cpu.read_float(0x8c34e0c8) == top + 12 + 22 * text.count('\n')
        cases.append({'kind': entry['kind'], 'index': entry['index'], 'row': entry['row'],
                      'panel_bounds': [left, top, left + PANEL_WIDTH, top + HEIGHT],
                      'glyph_bounds': bounds})
    print('Editor: 144 help messages and {} native caller/edge cases fit.'.format(len(cases)), flush=True)
    return {'unique_messages': 144, 'native_caller_cases': cases,
            'native_window_background_verified': True,
            'already_open_window_resized': True, 'actual_Flycast_playtest': False}
