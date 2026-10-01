"""Build v0.1.1 VWF support in place inside existing game code.

Default is a dry run. --build writes a new final data track in work/output.
Original tracks are never modified. No full Japanese scripts are exported.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct

from inspect_disc_text import Disc, ROOT
from sh4_patch import Assembler, pc_load
from cdrom_sector import regenerate

VERSION = '0.1.1'
BASE = 0x8c010000
SOURCE_SHA256 = '4526090cb90840370518beb404fe1ec45c6aa20ef0247c46134573a595a969bf'
CONVERTER_START, CONVERTER_END = 0x4f78, 0x50e0
WIDTH_TABLE = 0x898a8


def original_conversion(char):
    if not 32 <= char <= 122:
        return 0x8140
    exceptions = {96: 0x89fc, 44: 0x8143, 46: 0x8144, 58: 0x8146,
                  59: 0x8147, 63: 0x8148, 33: 0x8149, 94: 0x814f,
                  95: 0x8151, 47: 0x815e, 39: 0x8166, 40: 0x8169,
                  41: 0x816a, 43: 0x817b, 45: 0x817c, 36: 0x8190,
                  37: 0x8193, 35: 0x8194, 38: 0x8195, 42: 0x8196,
                  64: 0x81a5}
    return exceptions.get(char, char + (0x8220 if char > 90 else 0x821f))


def patched_conversion(char):
    # Preserve all legacy mappings, including the original backtick icon code.
    return {123: 0x816f, 124: 0x8162, 125: 0x8170, 126: 0x8160}.get(char, original_conversion(char))


def converter(address):
    a = Assembler(address)
    a.emit(0x604c, 0x70e0, 0xe15f, 0x3012)  # extu.b r4,r0; add #-32; 95; cmp/hs r1,r0
    a.branch(0x8900, 'space')
    a.emit(0x4000)
    # Table address follows code and two literals: 36 bytes total.
    a.load(1, address + 36)
    a.emit(0x001d, 0x600d, 0x000b, 0x0009)  # mov.w @(r0,r1),r0; extu.w; rts; nop
    a.label('space')
    a.load(0, 0x8140)
    a.emit(0x000b, 0x0009)
    code = a.finish()
    if len(code) != 36:
        raise ValueError('Unexpected converter layout')
    return code + struct.pack('<95H', *(patched_conversion(c) for c in range(32, 127)))


def numeric_measure(address, index_register, continuation):
    a = Assembler(address)
    a.emit(0x4f22)  # save incoming PR
    a.load(0, 0x8c34e114)
    a.emit(0x040c | index_register << 4, 0x644c)  # character from numeric buffer; unsigned
    a.load(0, BASE + CONVERTER_START)
    a.emit(0x400b, 0x0009, 0x6503)  # convert; mov r0,r5
    a.load(0, 0x8c01839c)
    a.emit(0x400b, 0xe401, 0x405a, 0xf02d, 0xff00, 0x4f26)
    a.load(0, BASE + continuation)
    a.emit(0x402b, 0x0009)
    return a.finish()


def plan(program, metrics=None):
    if hashlib.sha256(program).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unsupported 1ST_READ.BIN revision; original source hash does not match')
    patched = bytearray(program)
    changes = []

    def replace(offset, expected, replacement, purpose):
        expected = bytes.fromhex(expected) if isinstance(expected, str) else expected
        if bytes(patched[offset:offset + len(expected)]) != expected:
            raise ValueError('Unexpected source bytes at 0x{:x}'.format(offset))
        if len(expected) != len(replacement):
            raise ValueError('Patch must keep original file size')
        patched[offset:offset + len(replacement)] = replacement
        changes.append({'file_offset': offset, 'bytes': len(replacement), 'purpose': purpose,
                        'before_sha256': hashlib.sha256(expected).hexdigest(),
                        'after_sha256': hashlib.sha256(replacement).hexdigest()})

    code = converter(BASE + CONVERTER_START)
    code += b'\x09\x00' * ((-len(code) % 4) // 2)
    integer_helper = CONVERTER_START + len(code)
    code += numeric_measure(BASE + integer_helper, 11, 0x5ce0)
    float_helper = CONVERTER_START + len(code)
    code += numeric_measure(BASE + float_helper, 9, 0x5ef0)
    available = CONVERTER_END - CONVERTER_START
    if len(code) > available:
        raise ValueError('VWF helpers exceed reclaimed converter code space')
    used = len(code)
    code += b'\x09\x00' * ((available - len(code)) // 2)
    replace(CONVERTER_START, program[CONVERTER_START:CONVERTER_END], code,
            'Checked table converter plus proportional integer/decimal measurement helpers')
    for offset, helper, literal in ((0x5cda, integer_helper, 0x5da0),
                                     (0x5eea, float_helper, 0x5fc0)):
        replace(offset, program[offset:offset + 6],
                struct.pack('<3H', pc_load(0, BASE + offset, BASE + literal), 0x402b, 0x0009),
                'Measure numeric readout with the same cached glyph widths used to draw it')
        replace(literal, '00008041', struct.pack('<I', BASE + helper), 'Measurement helper address')
    for offset in (0x5db8, 0x5fd8, 0x639c):
        replace(offset, 'e47d018c', struct.pack('<I', 0x8c017f64),
                'Use proportional cached renderer for numeric/fixed-font text')
    if metrics is not None:
        if metrics.get('source_program_sha256') != SOURCE_SHA256:
            raise ValueError('Metrics refer to a different source revision')
        widths = bytearray()
        for i, row in enumerate(metrics['glyphs']):
            if row['code'] != 32 + i or not isinstance(row['ink_width'], int) or not 0 <= row['ink_width'] <= 12:
                raise ValueError('Invalid native Latin font metric')
            widths.append(row['ink_width'])
        if len(widths) != 95:
            raise ValueError('Expected 95 printable ASCII metrics')
        if metrics.get('native_tracking') != 2:
            raise ValueError('Native tracking is currently fixed at 2 pixels')
        replace(WIDTH_TABLE, program[WIDTH_TABLE:WIDTH_TABLE + 95], widths, 'Native Latin width table')
    report = {'version': VERSION, 'source_program_sha256': SOURCE_SHA256,
              'target_program_sha256': hashlib.sha256(patched).hexdigest(),
              'program_bytes': len(program), 'code_space_available': available,
              'code_space_used': used, 'integer_helper': integer_helper, 'decimal_helper': float_helper,
              'scope': 'Native proportional cached font modes 1/4 and integer/decimal readouts; existing modes 0/2/3 and control parsing retained',
              'changes': changes}
    return bytes(patched), report


def make_metrics(program):
    return {'version': VERSION, 'source_program_sha256': SOURCE_SHA256,
            'native_tracking': 2, 'native_font': '/DATAFILE/HANKAKU_P.PVR',
            'native_cell_pitch': 12, 'native_render_height': 12,
            'large_font': 'Existing BIOS glyph cache; runtime ink bounds plus 4 pixels',
            'glyphs': [{'code': c, 'character': chr(c), 'ink_width': program[WIDTH_TABLE + c - 32],
                        'advance': program[WIDTH_TABLE + c - 32] + 2} for c in range(32, 127)]}


def write_track(disc, entry, original, target, output):
    start, end, source = next(t for t in disc.tracks if t[0] <= entry['lba'] < t[1])
    if (entry['lba'] + (len(target) + 2047) // 2048) > end:
        raise ValueError('Patched file crosses a source track')
    shutil.copyfile(str(source), str(output))
    changed = []
    with output.open('r+b') as stream:
        for index in range((len(target) + 2047) // 2048):
            offset = index * 2048
            if original[offset:offset + 2048] == target[offset:offset + 2048]:
                continue
            position = (entry['lba'] - start + index) * 2352
            stream.seek(position)
            sector = stream.read(2352)
            if regenerate(sector) != sector:
                raise ValueError('Original changed sector has invalid EDC/ECC')
            replacement = bytearray(sector)
            chunk = target[offset:offset + 2048]
            replacement[16:16 + len(chunk)] = chunk
            replacement = regenerate(replacement)
            stream.seek(position)
            stream.write(replacement)
            changed.append({'lba': entry['lba'] + index, 'track_offset': position})
    return changed


def gdi(disc, patched_track, output):
    lines = ['17']
    source_paths = sorted(ROOT.glob('*Track*.bin'))
    starts = {int(__import__('re').search(r'Track (\d+)', t[2].name).group(1)): t[0] for t in disc.tracks}
    starts.update({1: 0, 2: source_paths[0].stat().st_size // 2352})
    for number, source in enumerate(source_paths, 1):
        pregap = 0 if number in (1, 3) else 225 if number == 17 else 150
        path = patched_track if number == 17 else source
        # Relative paths also let the whole workspace move without breaking the set.
        filename = Path(os.path.relpath(str(path), str(output.parent))).as_posix()
        lines.append('{} {} {} 2352 "{}" {}'.format(number, starts[number] + pregap,
                     4 if number in (1, 3, 17) else 0, filename, pregap * 2352))
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--metrics', type=Path)
    args = parser.parse_args()
    disc = Disc()
    entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
    original = disc.read(entry['lba'], entry['size'])
    metrics = json.loads(args.metrics.read_text(encoding='utf-8')) if args.metrics else None
    target, report = plan(original, metrics)
    print(json.dumps(report, indent=2))
    if not args.build:
        print('Dry run only. No image or inventory files written.')
        return
    folder = ROOT / 'work' / 'output' / ('vwf-' + VERSION)
    folder.mkdir(parents=True, exist_ok=False)
    patched_track = folder / ('Marionette Handler 2 (Japan) (Track 17) VWF ' + VERSION + '.bin')
    report['modified_sectors'] = write_track(disc, entry, original, target, patched_track)
    report['runtime_validation'] = 'See work/ui/vwf_validation.json; limited SH-4 harness, not an emulator playtest'
    (folder / 'PATCH-REPORT.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    gdi(disc, patched_track, folder / ('Marionette Handler 2 VWF ' + VERSION + '.gdi'))
    cue = next(ROOT.glob('*.cue')).read_text(encoding='utf-8')
    for source in sorted(ROOT.glob('*Track*.bin')):
        path = patched_track if '(Track 17)' in source.name else source
        filename = Path(os.path.relpath(str(path), str(folder))).as_posix()
        cue = cue.replace('"' + source.name + '"', '"' + filename + '"')
    (folder / ('Marionette Handler 2 VWF ' + VERSION + '.cue')).write_text(cue, encoding='utf-8')
    path = ROOT / 'work' / 'ui' / 'vwf_metrics.json'
    if not path.exists():
        path.write_text(json.dumps(make_metrics(original), indent=2), encoding='utf-8')
    print('Test build:', folder)


if __name__ == '__main__':
    main()
