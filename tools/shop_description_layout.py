"""Restore native VWF in shop help mode and wrap the eleven part descriptions."""
import hashlib
import json
import struct

from build_vwf import BASE, patched_conversion
from build_english import prepare_native_cache
from full_english import batches, merged
from sh4_patch import Assembler, pc_load
from validate_vwf import CPU
from inspect_disc_text import ROOT

VERSION = '0.1.12'
SPACE = 6
WIDTH = 300


def hook(result, at, destination):
    result[at:at + 12] = struct.pack('<4HI', pc_load(0, BASE + at, BASE + at + 8),
                                   0x402b, 0x0009, 0x0009, destination)


def plan(original, program, report):
    result = bytearray(program)
    changes = list(report['changed_regions'])
    fixed = struct.pack('<I', BASE + 0x8100)
    refs = [i for i in range(len(program) - 3) if program[i:i + 4] == fixed]
    assert refs == [0x63d8, 0x6a24], refs
    for pc in range(0x5bd0, 0x9000, 2):
        if 0x8100 <= pc < 0x82a4 or 0x7f2c <= pc < 0x7f64 or 0x80c4 <= pc < 0x8100:
            continue  # Verified literal pools are data, not instructions.
        word = struct.unpack_from('<H', program, pc)[0]
        if word >> 12 == 0xd:
            literal = ((pc + 4) & ~3) + (word & 255) * 4
            assert not 0x8100 <= literal < 0x82a4, ('Shared fixed-renderer pool', pc, literal)
        if word >> 12 in (0xa, 0xb):
            displacement = word & 0xfff
            if displacement & 0x800:
                displacement -= 4096
            assert pc + 4 + displacement * 2 != 0x8100, ('Direct fixed-renderer caller', pc)
    for at in refs:
        struct.pack_into('<I', result, at, BASE + 0x7f64)
        changes.append((at, at + 4))
    # The fixed renderer is now unreachable. Reuse only its own code/pool;
    # the next independently called routine starts at 0x82a4.
    assert program[0x8100:0x82a4] == original[0x8100:0x82a4]
    start = BASE + 0x8100
    a = Assembler(start)
    a.load(0, patched_conversion(32))
    a.emit(0x3040)
    a.branch(0x8b00, 'normal')
    marker = 0x12345678
    a.load(0, marker)
    a.emit(0xf008, 0x000b, 0x0009)
    a.label('normal')
    a.emit(*struct.unpack('<6H', program[0x7f64:0x7f70]))
    a.load(0, BASE + 0x7f70)
    a.emit(0x402b, 0x0009)
    draw = a.finish()
    draw = draw.replace(struct.pack('<I', marker), struct.pack('<I', start + len(draw)))
    draw += struct.pack('<f', float(SPACE))
    measure_start = start + len(draw)
    a = Assembler(measure_start)
    a.load(0, patched_conversion(32))
    a.emit(0x3050)
    a.branch(0x8b00, 'normal')
    a.emit(0xe000 | SPACE, 0x000b, 0x0009)
    a.label('normal')
    a.load(7, 613)
    a.emit(0xe400, 0xe314, 0x6643)
    a.load(0, BASE + 0x83c4)
    a.emit(0x402b, 0x0009)
    measure = a.finish()
    background_start = measure_start + len(measure)
    a = Assembler(background_start)
    constants = []

    def number(value):
        marker = 0x12340000 + len(constants)
        constants.append((marker, float(value)))
        a.load(0, marker)
        a.emit(0xf008)

    a.load(0, 0x8c1b20e4)
    a.emit(0x6002, 0x8801)
    a.branch(0x8b00, 'font')
    a.emit(0x4f22)
    for global_at, add, low, high, span in (
            (0x8c36b06c, 7, 0x8c1a34e4, 0x8c1a34ec, 320),
            (0x8c36b070, 75, 0x8c1a34e8, 0x8c1a34f0, 252)):
        a.load(0, global_at)
        a.emit(0xf108)
        number(add)
        a.emit(0xf100)
        a.load(1, low)
        a.emit(0xf11a)
        number(span)
        a.emit(0xf100)
        a.load(1, high)
        a.emit(0xf11a)
    a.load(0, 0x8c36b074)
    a.emit(0xf408)
    number(29)
    a.emit(0xf400)
    a.load(0, 0x8c36b08c)
    a.emit(0x6102)
    a.load(4, 255)
    a.emit(0x3418, 0x4428, 0x4418)
    a.load(0, 0x00101010)
    a.emit(0x240b)
    a.load(0, BASE + 0x904c)
    a.emit(0x400b, 0x0009, 0x4f26)
    a.label('font')
    a.emit(0x4f22)
    a.load(0, BASE + 0x5bd0)
    a.emit(0x400b, 0xe401, 0x4f26)
    a.load(0, 0x8c36b08c)
    a.load(4, 255)
    a.emit(0x6102, 0x3418)
    a.load(0, BASE + 0x58b9c)
    a.emit(0x402b, 0x0009)
    background = a.finish()
    for marker, value in constants:
        background = background.replace(struct.pack('<I', marker),
                                        struct.pack('<I', background_start + len(background)))
        background += struct.pack('<f', value)
    assert len(draw + measure + background) <= 0x82a4 - 0x8100
    result[0x8100:0x82a4] = (draw + measure + background).ljust(0x82a4 - 0x8100, b'\0')
    hook(result, 0x7f64, start)
    hook(result, 0x83b8, measure_start)
    hook(result, 0x58b90, background_start)
    changes += [(0x8100, 0x82a4), (0x7f64, 0x7f70), (0x83b8, 0x83c4), (0x58b90, 0x58b9c)]
    metrics = {r['character']: r['advance'] for r in report['font_asset']['latin_metrics']}
    metrics[' '] = SPACE
    policy = json.loads((ROOT / 'work/translation/en/shop_description_layout.json').read_text())
    assert policy['version'] == VERSION and policy['space_advance_px'] == SPACE
    assert policy['max_line_advance_px'] == WIDTH
    approved = {row['row']: row['target'] for row in policy['translations']}
    _, texts, _ = batches()
    overrides, layouts = {}, []
    for ordinal in range(324, 335):
        source = texts[ordinal - 1]
        header, body = source.split('\n', 1)
        assert '\n\n' not in body
        lines, line = [], ''
        for word in body.split():
            assert sum(metrics[c] for c in word) <= WIDTH, word
            candidate = line + (' ' if line else '') + word
            if sum(metrics[c] for c in candidate) > WIDTH:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
        text = header + '\n' + '\n'.join(lines)
        if source.endswith('\n'):
            text += '\n'
        assert text == approved[ordinal], 'Layout policy and compiled wrapping differ'
        assert ' '.join(source.split()) == ' '.join(text.split())
        assert len(source.encode('ascii')) == len(text.encode('ascii'))
        binding = report['bindings'][ordinal - 1]
        at = binding['target_file_offset']
        assert result[at:at + len(source)] == source.encode('ascii')
        result[at:at + len(text)] = text.encode('ascii')
        binding.update(target_sha256=hashlib.sha256(text.encode('ascii')).hexdigest(),
                       line_count=text.count('\n') + 1)
        changes.append((at, at + len(text)))
        overrides[str(ordinal)] = text
        layouts.append({'row': ordinal, 'id': binding['id'], 'target': text,
                        'line_advances': [sum(metrics[c] for c in line) for line in text.split('\n')],
                        'words_preserved': True})
    report.update(version=VERSION, space_advance_px=SPACE, layout_overrides=overrides,
                  shop_description_layout={'max_line_advance': WIDTH, 'panel_width': 320,
                                           'text_origin_x': 12, 'descriptions': layouts,
                                           'background': {'caller_hook': 0x58b90, 'parts_category': 1,
                                                          'relative_rect': [7, 75, 327, 327],
                                                          'depth_above_window': 29, 'follows_help_fade': True},
                                           'renderer_call_literals': refs},
                  changed_regions=merged(changes),
                  target_program_sha256=hashlib.sha256(result).hexdigest())
    allowed = bytearray(len(program))
    for a, z in changes:
        allowed[a:z] = b'\1' * (z - a)
    assert len(result) == len(program)
    assert all(a == b or allowed[i] for i, (a, b) in enumerate(zip(program, result)))
    return bytes(result)


def validate(program, report, metrics):
    template, _, codes, _ = prepare_native_cache(program)
    for index, code in enumerate(codes):
        bearing, advance = metrics[code]
        template.write(0x8c34dbb4 + index, bearing, 1)
        template.write(0x8c34de28 + index, advance, 1)

    def setup():
        cpu = CPU(program)
        cpu.mem[0x34d6d0:0x34e0c0] = template.mem[0x34d6d0:0x34e0c0]
        cpu.write_float(0x8c13d758, 1)
        return cpu

    def width(text):
        return sum(SPACE if c == ' ' else metrics[patched_conversion(ord(c))][1] for c in text)

    evidence = []
    for row in report['shop_description_layout']['descriptions']:
        cpu = setup()
        cpu.write(0x8c13d75c, 3)
        cpu.write_float(0x8c34e0c0, 12)
        cpu.write_float(0x8c34e0c4, 12)
        cpu.write_float(0x8c34e0c8, 154)
        cpu.f[4] = 400
        vertices = []

        def submit():
            vertices.extend((cpu.read_float(cpu.r[4] + i * 24),
                             cpu.read_float(cpu.r[4] + i * 24 + 4)) for i in range(4))
            cpu.submit()

        cpu.stubs[0x8c1731a4] = submit
        binding = report['bindings'][row['row'] - 1]
        cpu.r[4] = BASE + binding['target_file_offset']
        cpu.run(BASE + 0x6090, limit=3000000)
        left, right = min(x for x, y in vertices), max(x for x, y in vertices)
        bottom = max(y for x, y in vertices)
        assert 0 <= left <= right <= 320 and bottom < 480, (row['row'], left, right, bottom)
        assert cpu.read_float(0x8c34e0c0) == 12 + width(row['target'].split('\n')[-1])
        assert cpu.r[15] == 0x8cf00000
        evidence.append({'row': row['row'], 'quad_bounds': [left, 154, right, bottom],
                         'line_count': binding['line_count']})
    popup_cases = []
    for category, fade, selected in [(1, 0, i) for i in range(11)] + [(1, 128, 0), (1, 255, 0)] + [(i, 0, 0) for i in (0, 2, 3, 4)]:
        cpu = setup()
        cpu.write(0x8c1b20e4, category)
        cpu.write(0x8c1b20e0, selected)
        cpu.write_float(0x8c36b06c, 63)
        cpu.write_float(0x8c36b070, 75)
        cpu.write_float(0x8c36b074, 100)
        cpu.write(0x8c36b08c, fade)
        backgrounds = []

        def rectangle():
            backgrounds.append({'vertices': [cpu.read_float(0x8c1a34e4 + i * 4) for i in range(8)],
                                'depth': cpu.f[4], 'color': cpu.read(0x8c1a345c)})

        cpu.stubs[0x8c176654] = rectangle
        cpu.run(BASE + 0x58b8e, stop=BASE + 0x58b9c)
        assert cpu.r[15] == 0x8cf00000 and cpu.read(0x8c13d75c) == 1
        assert cpu.r[4] == 255 - fade
        if category != 1:
            assert not backgrounds
            continue
        assert backgrounds == [{'vertices': [70, 150, 70, 402, 390, 402, 390, 150],
                                'depth': 129, 'color': ((255 - fade) << 24) | 0x101010}]
        cpu.run(BASE + 0x58b9c, stop=BASE + 0x58bf0, limit=3000000)
        assert cpu.r[15] == 0x8cf00000
        assert 70 <= min(min(v) for v in cpu.vertices) <= max(max(v) for v in cpu.vertices) <= 390
        text = report['layout_overrides'][str(324 + selected)]
        assert cpu.read_float(0x8c34e0c8) == 154 + 22 * (len(text.split('\n')) - 1)
        assert cpu.read_float(0x8c34e0c8) + (0 if text.endswith('\n') else 19) <= 402
        popup_cases.append({'row': 324 + selected, 'fade': fade, 'bounds': [70, 150, 390, 402],
                            'actual_native_caller_verified': True})
    measured = []
    for char in ('W', 'i', 'l', ' ', '\u3000'):
        code = patched_conversion(ord(char)) if char.isascii() else 0x8140
        cpu = setup()
        cpu.r[4:6] = [1, code]
        cpu.run(BASE + 0x839c)
        expected = SPACE if char == ' ' else metrics.get(code, (0, 20))[1]
        assert cpu.r[0] == expected
        cpu = setup()
        cpu.r[4], cpu.f[4], cpu.f[5] = code, 50, 40
        cpu.run(BASE + 0x7f64)
        assert cpu.f[0] == expected and cpu.r[15] == 0x8cf00000
        measured.append({'character': char, 'advance': expected})
    cpu = setup()
    sample = 'Wi il'
    blob = b''.join(patched_conversion(ord(c)).to_bytes(2, 'big') for c in sample) + b'\0'
    cpu.mem[0xe00000:0xe00000 + len(blob)] = blob
    cpu.write(0x8c34e0e8, 0x8ce00000)
    cpu.r[14] = 0
    cpu.f[13:16] = [1, 40, 50]
    for char in sample:
        cpu.run(BASE + 0x6994, stop=BASE + 0x69cc, limit=100000)
    assert cpu.f[15] == 50 + width(sample) and len(cpu.vertices) == 4, (cpu.f[15], width(sample), cpu.vertices)
    print('Shop: all 11 mode-3 descriptions fit; VWF drawing, measurement and scrolling verified.', flush=True)
    return {'descriptions': evidence, 'glyph_advances': measured,
            'native_popup_cases': popup_cases, 'other_categories_no_background': 4,
            'scrolling_native_draw_verified': True, 'actual_Flycast_playtest': False}
