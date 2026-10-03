"""Translate four screenshot labels using native texture and string storage."""
import hashlib
import json
import struct

from PIL import Image, ImageDraw, ImageFont

import bizin_font
from build_vwf import BASE, patched_conversion
from full_english import merged
from inspect_disc_text import ROOT
from pvr_ui import decode, encode_rectangles, layout, address
from validate_vwf import CPU
from build_english import prepare_native_cache

VERSION = '0.1.11'
POOL_BASE = 0x13d9f8
SHOP_SHA = '824827b653c7f8fb1f217934a007e0c27e2cab39295f82411979a85fa5a834ef'
CARD_WIDTH = 159


def rows():
    data = json.loads((ROOT / 'work/translation/en/shop_account_ui.json').read_text(encoding='utf-8'))
    assert data['version'] == VERSION and data['language'] == 'en'
    return data['translations']


def account_plan(original, program, report):
    result = bytearray(program)
    free = [list(pair) for pair in report['allocation']['free_fragments']]
    changes = list(report['changed_regions'])
    bindings = []
    for row in rows():
        if row['file'] != '/1ST_READ.BIN':
            continue
        old = row['source'].encode('cp932')
        source = row['source_offset']
        assert original[source:source + len(old) + 1] == old + b'\0'
        assert result[source:source + len(old) + 1] == old + b'\0'
        text = row['target'].encode('ascii') + b'\0'
        choices = [(z - a - len(text), i, a) for i, (a, z) in enumerate(free) if a + len(text) <= z]
        assert choices, 'No verified free bank fits the complete account label'
        _, index, target = min(choices)
        result[target:target + len(text)] = text
        free[index][0] = target + len(text)
        changes.append((target, target + len(text)))
        literal = row['relative_pointer_literal']
        assert struct.unpack_from('<I', result, literal)[0] == source - POOL_BASE
        # These routines compute r4 = pool base + relative string displacement.
        references = []
        for pc in range(0, len(program) - 1, 2):
            word = struct.unpack_from('<H', program, pc)[0]
            if word >> 12 == 0xd and ((pc + 4) & ~3) + (word & 255) * 4 == literal:
                references.append(pc)
        assert references == [row['draw_pointer_start'] + 2], references
        struct.pack_into('<I', result, literal, (target - POOL_BASE) & 0xffffffff)
        changes.append((literal, literal + 4))
        x_at = row['x_literal']
        assert struct.unpack_from('<f', result, x_at)[0] == row['original_x']
        x_refs = [pc for pc in range(0, len(program) - 1, 2)
                  if struct.unpack_from('<H', program, pc)[0] >> 8 == 0xc7
                  and ((pc + 4) & ~3) + (program[pc] * 4) == x_at]
        assert len(x_refs) == 1 and row['draw_start'] <= x_refs[0] < row['draw_pointer_start']
        struct.pack_into('<f', result, x_at, row['target_x'])
        changes.append((x_at, x_at + 4))
        bindings.append({**row, 'source_sha256': hashlib.sha256(old).hexdigest(),
                         'target_offset': target, 'target_bytes': len(text) - 1})
    # Guard every byte changed relative to the established Bizin/t font plan.
    allowed = bytearray(len(program))
    for row in bindings:
        for a, z in [(row['target_offset'], row['target_offset'] + row['target_bytes'] + 1),
                     (row['relative_pointer_literal'], row['relative_pointer_literal'] + 4),
                     (row['x_literal'], row['x_literal'] + 4)]:
            allowed[a:z] = b'\1' * (z - a)
    assert len(result) == len(program)
    assert all(a == b or allowed[i] for i, (a, b) in enumerate(zip(program, result)))
    report.update(version=VERSION, target_program_sha256=hashlib.sha256(result).hexdigest(),
                  changed_regions=merged(changes), account_ui_bindings=bindings,
                  additional_ui_labels=4, additional_native_text_labels=2,
                  additional_texture_labels=2)
    report['allocation']['free_fragments'] = free
    report['allocation']['remaining_fragment_bytes'] = sum(z - a for a, z in free)
    return bytes(result)


def shop_plan(disc):
    entry = next(e for e in disc.files if e['path'] == '/DATAFILE/SHOP_00.PVR')
    original = disc.read(entry['lba'], entry['size'])
    assert hashlib.sha256(original).hexdigest() == SHOP_SHA
    before = decode(original)
    after = before.copy()
    # Render native texture glyphs, not a Flycast replacement pack. Supersampling
    # supplies coverage for the original ARGB4444 alpha channel.
    scale = 4
    font = ImageFont.truetype(str(bizin_font.FONT), 18 * scale)
    boxes = [font.getbbox(text, anchor='ls') for text in ('Buy', 'Sell')]
    top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
    horizontal = min(1.0, 30 * scale / max(b[2] - b[0] for b in boxes))
    vertical = min(1.0, 15 * scale / (bottom - top))
    rectangles = []
    for row in rows():
        if row['file'] != entry['path']:
            continue
        rect = row['rectangle']
        left, y0, right, y1 = rect
        assert (right - left, y1 - y0) == (32, 16)
        text = row['target']
        box = font.getbbox(text, anchor='ls')
        mask = Image.new('L', (box[2] - box[0], bottom - top))
        ImageDraw.Draw(mask).text((-box[0], -top), text, anchor='ls', font=font, fill=255)
        mask = mask.resize((max(1, round(mask.width * horizontal / scale)),
                            max(1, round(mask.height * vertical / scale))), Image.Resampling.LANCZOS)
        glyph = Image.new('RGBA', mask.size, (255, 255, 255, 0))
        glyph.putalpha(mask)
        after.paste((0, 0, 0, 0), rect)
        after.paste(glyph, (left + (32 - glyph.width) // 2, y0 + (16 - glyph.height) // 2))
        rectangles.append(rect)
    target = encode_rectangles(original, after, rectangles)
    quantized = decode(target)
    base, pixel, width, height = layout(original)
    allowed = bytearray(len(original))
    for left, top, right, bottom in rectangles:
        assert quantized.crop((left, top, right, bottom)).getbbox()
        for y in range(top, bottom):
            for x in range(left, right):
                at = base + address(x, y)
                allowed[at:at + 2] = b'\1\1'
    assert len(target) == len(original)
    assert all(a == b or allowed[i] for i, (a, b) in enumerate(zip(original, target)))
    # Decode/encode of the complete source texture is exactly reversible.
    assert encode_rectangles(original, before, [(0, 0, width, height)]) == original
    return entry, target, {'file': entry['path'], 'lba': entry['lba'], 'size': entry['size'],
                          'source_sha256': SHOP_SHA, 'target_sha256': hashlib.sha256(target).hexdigest(),
                          'dimensions': [width, height], 'format': 'ARGB4444 square twiddled',
                          'rectangles': rectangles, 'labels': ['Buy', 'Sell'],
                          'font': 'Bizin Gothic Bold v0.0.4',
                          'pixels_outside_rectangles_byte_identical': True,
                          'header_and_storage_length_unchanged': True,
                          'source_pixel_round_trip_exact': True, 'texture_replacement': False}, before, quantized


def validate_account(program, report, metrics):
    template, _, codes, _ = prepare_native_cache(program)
    for index, code in enumerate(codes):
        bearing, advance = metrics[code]
        template.write(0x8c34dbb4 + index, bearing, 1)
        template.write(0x8c34de28 + index, advance, 1)
    evidence = []
    for row in report['account_ui_bindings']:
        cpu = CPU(program)
        cpu.mem[0x34d6d0:0x34e0c0] = template.mem[0x34d6d0:0x34e0c0]
        cpu.write(0x8c13d75c, 1)
        cpu.write_float(0x8c36b078, 0.0)
        cpu.write_float(0x8c36b07c, 0.0)
        cpu.write_float(0x8c36b080, -100.0)
        cpu.f[4] = 400.0
        cpu.run(BASE + row['draw_start'], stop=BASE + row['draw_pointer_start'])
        origin = cpu.read_float(0x8c34e0c0)
        assert origin == row['target_x']
        cpu.run(BASE + row['draw_pointer_start'], stop=BASE + row['draw_pointer_start'] + 6)
        assert cpu.r[4] == BASE + row['target_offset']
        cpu.run(BASE + row['draw_pointer_start'] + 6, stop=BASE + row['draw_end'], limit=3000000)
        width = sum(metrics.get(patched_conversion(ord(c)), (0, 20))[1] for c in row['target'])
        assert cpu.f[0] == origin + width
        assert cpu.r[15] == 0x8cf00000 and len(cpu.vertices) == len(row['target'].replace(' ', ''))
        ink_left = min(min(v) for v in cpu.vertices)
        ink_right = max(max(v) for v in cpu.vertices)
        assert 0 <= ink_left <= ink_right <= CARD_WIDTH, (row['id'], ink_left, ink_right)
        evidence.append({'id': row['id'], 'text': row['target'], 'advance': width,
                         'origin_x': origin, 'ink_bounds_x': [ink_left, ink_right],
                         'card_right_x': CARD_WIDTH, 'native_caller_pointer_verified': True,
                         'native_dispatch_and_stack_verified': True})
    print('Account: both native callers, complete English draws and card widths verified.', flush=True)
    return {'cases': evidence, 'actual_Flycast_playtest': False}


def preview(before, after):
    # Preview only the changed native atlas slots, enlarged for inspection.
    panel = Image.new('RGB', (640,180), '#111111')
    draw = ImageDraw.Draw(panel)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 18)
    draw.text((12, 8), 'Original shop labels', font=font, fill='white')
    draw.text((330, 8), VERSION + ' — Bizin Gothic Bold', font=font, fill='white')
    for col, image in enumerate((before, after)):
        crop = image.crop((180, 24, 244, 40)).resize((288, 72), Image.Resampling.NEAREST)
        panel.paste(crop, (12 + col * 318, 48), crop)
    draw.text((12,140), 'Native texture slots; Flycast filtering affects the final display.', font=font, fill='#bbbbbb')
    return panel
