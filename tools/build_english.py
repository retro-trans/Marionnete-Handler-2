"""Build cumulative English UI batches on top of VWF, defaulting to a read-only plan.

Repack one verified, contiguous message bank and retarget every verified
absolute reference. Text is not truncated to individual original slots.
Dialogue is outside this batch and will require separate relocation storage.
Original tracks, executable length and ISO directory remain unchanged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import struct

from inspect_disc_text import Disc, ROOT
from build_vwf import BASE, SOURCE_SHA256, WIDTH_TABLE, patched_conversion, plan as vwf_plan, write_track, gdi
from cdrom_sector import regenerate

VERSION = '0.1.3'
RELEASE_BATCHES = {'0.1.2': 1, '0.1.3': 2}


def load_batches(version):
    batches = []
    for number in range(1, RELEASE_BATCHES[version] + 1):
        path = ROOT / 'work' / 'translation' / 'en' / ('ui_batch_{:03d}.json'.format(number))
        batch = json.loads(path.read_text(encoding='utf-8'))
        expected_version = ('0.1.2', '0.1.3')[number - 1]
        if (batch['version'] != expected_version or batch['language'] != 'en'
                or batch['source_program_sha256'] != SOURCE_SHA256):
            raise ValueError('Unsupported translation version, language or source')
        if (len(batch['translations']) != 80 or batch['slice']['first_row'] != (number - 1) * 80 + 1
                or batch['slice']['last_row'] != number * 80):
            raise ValueError('Expected consecutive reviewed 80-row menu slices')
        batches.append((path, batch))
    return batches


def inventory_path(version):
    name = 'english_batch_001_inventory.json' if version == '0.1.2' else 'english_' + version + '_inventory.json'
    return ROOT / 'work' / 'ui' / name


def digest(value):
    return hashlib.sha256(value).hexdigest()


def source_rows():
    inventory = json.loads((ROOT / 'work' / 'ui' / 'text_inventory.json').read_text(encoding='utf-8'))
    return sorted((r for r in inventory['entries'] if r['category'] == 'menus_prompts_help_and_descriptions'),
                  key=lambda r: r['file_offset'])


def plan(original, version=VERSION):
    batches = load_batches(version)
    targets = [text for _, batch in batches for text in batch['translations']]
    notes = {key: note for _, batch in batches for key, note in batch['notes'].items()}
    glossary = json.loads((ROOT / 'work' / 'glossary' / 'en.json').read_text(encoding='utf-8'))
    rows = source_rows()
    selected = rows[:len(targets)]
    start, end = selected[0]['file_offset'], rows[len(targets)]['file_offset']
    cursor = start
    for row in selected:
        if row['file_offset'] != cursor:
            raise ValueError('Message bank contains an unreviewed gap')
        raw = original[cursor:cursor + row['source_bytes']]
        if digest(raw) != row['source_sha256'] or original[cursor + len(raw)] != 0:
            raise ValueError('Message source/terminator mismatch')
        cursor += len(raw) + 1
    if cursor != end:
        raise ValueError('Message bank end is not the next untranslated record')
    pointer_starts = {BASE + row['file_offset'] for row in selected}
    for offset in range(0, len(original) - 3, 4):
        address = struct.unpack_from('<I', original, offset)[0]
        if BASE + start <= address < BASE + end and address not in pointer_starts:
            raise ValueError('Unreviewed reference into a message interior: 0x{:x}'.format(offset))
    vwf, vwf_report = vwf_plan(original)
    patched = bytearray(vwf)
    packed = bytearray()
    bindings = []
    for ordinal, (row, text) in enumerate(zip(selected, targets), 1):
        raw = original[row['file_offset']:row['file_offset'] + row['source_bytes']]
        source = raw.decode('cp932')
        target = text.encode('ascii')
        if any(byte != 10 and not 32 <= byte <= 126 for byte in target):
            raise ValueError('Unsupported target character/control in row {}'.format(ordinal))
        if source.count('\n') != text.count('\n'):
            raise ValueError('Review newline count change before building row {}'.format(ordinal))
        # General control-token guard, even though this batch contains none.
        controls = r'@[a-zA-Z]\d{3}|%[-+ #0]*\d*(?:\.\d+)?[diuoxXfFeEgGcs]|\\[nrt]'
        if re.findall(controls, source) != re.findall(controls, text):
            raise ValueError('Control/placeholder mismatch in row {}'.format(ordinal))
        for term in glossary['terms']:
            if term['source'] not in source:
                continue
            allowed = (term['target'], term.get('plural', term['target']), term.get('adjective', term['target']))
            if not any(spelling.casefold() in text.casefold() for spelling in allowed):
                raise ValueError('Glossary mismatch in row {}: {}'.format(ordinal, term['target']))
        new_offset = start + len(packed)
        old_pointer = struct.pack('<I', BASE + row['file_offset'])
        references = []
        at = original.find(old_pointer)
        while at >= 0:
            references.append(at)
            at = original.find(old_pointer, at + 1)
        if references != row['absolute_pointer_locations'] or not references:
            raise ValueError('Inventory does not account for every source pointer')
        for reference in references:
            if start <= reference < end:
                raise ValueError('Pointer overlaps translation bank')
            struct.pack_into('<I', patched, reference, BASE + new_offset)
        packed += target + b'\x00'
        small_widths = [sum(original[WIDTH_TABLE + ord(c) - 32] + 2 for c in line)
                        for line in text.split('\n')]
        bindings.append({'row': ordinal, 'id': row['id'], 'source_sha256': row['source_sha256'],
                         'source_file_offset': row['file_offset'], 'target_file_offset': new_offset,
                         'target_bytes': len(target), 'target_sha256': digest(target),
                         'pointer_locations': references, 'line_count': len(text.split('\n')),
                         'small_font_line_widths_px': small_widths,
                         'line_characters': [len(line) for line in text.split('\n')],
                         'source_line_characters': [len(line) for line in source.split('\n')],
                         'layout_status': 'Needs actual cached-font metrics and in-game popup verification',
                         'review_note': notes.get(str(ordinal))})
    if len(packed) > end - start:
        raise ValueError('Full translations exceed this shared UI bank; add storage relocation, do not truncate text')
    patched[start:end] = packed + b'\x00' * (end - start - len(packed))
    report = {'version': version, 'language': 'en', 'translated_game_entries': len(targets),
              'inventoried_game_entries': 793, 'network_entries_translated': 0,
              'batches': [{'file': path.name, 'sha256': digest(path.read_bytes()),
                           'slice': batch['slice'], 'meaning_review': batch['review']}
                          for path, batch in batches],
              'source_program_sha256': digest(original), 'target_program_sha256': digest(patched),
              'program_bytes': len(patched), 'bank': {'start': start, 'end': end,
              'available': end - start, 'used': len(packed), 'individual_slot_limits': False},
              'retargeted_pointer_locations': sum(len(b['pointer_locations']) for b in bindings),
              'vwf': vwf_report,
              'layout': {'source_observed_max_line_characters': max(max(b['source_line_characters']) for b in bindings),
                         'english_max_line_characters': max(max(b['line_characters']) for b in bindings),
                         'english_max_small_font_line_width_px': max(max(b['small_font_line_widths_px']) for b in bindings),
                         'approved_ui_character_limit': None,
                         'note': 'Observed lengths describe this batch, not a verified textbox limit. Small-font pixel widths are exact native metrics; this popup uses cached-font mode 1, whose BIOS advances require runtime measurement.'},
              'bindings': bindings, 'limitations': ['Only the first {} menu/system/shop messages are translated.'.format(len(targets)),
              'No dialogue, browser messages or texture text translated.',
              'Cached-font advances and popup boundaries require emulator/hardware verification.',
              'Source omission/equipment-context flags remain in the translation batch.']}
    validate_program(original, bytes(patched), report, targets)
    return bytes(patched), report


def validate_program(original, target, report, texts):
    assert len(original) == len(target)
    start, end = report['bank']['start'], report['bank']['end']
    regions = [(start, end)]
    regions += [(c['file_offset'], c['file_offset'] + c['bytes']) for c in report['vwf']['changes']]
    for binding, text in zip(report['bindings'], texts):
        offset = binding['target_file_offset']
        assert target[offset:target.index(b'\x00', offset)].decode('ascii') == text
        for pointer in binding['pointer_locations']:
            assert struct.unpack_from('<I', target, pointer)[0] == BASE + offset
            regions.append((pointer, pointer + 4))
    covered = bytearray(len(original))
    for a, b in regions:
        covered[a:b] = b'\x01' * (b - a)
    assert all(a == b or covered[i] for i, (a, b) in enumerate(zip(original, target)))


def prepare_native_cache(target):
    from validate_vwf import CPU
    cpu = CPU(target)
    reverse = {patched_conversion(char): char for char in range(32, 127)}
    widths = {char: 20 for char in range(32, 127)}
    generated = []

    def glyph():
        index = cpu.read(0x8c34e0ac)
        code = cpu.read(0x8c34d6d0 + 2 * index, 2)
        char = reverse.get(code)
        width = 6 if char in (32, 44, 46) else 8 if char == 49 else 11 + char % 5 if char is not None else 20
        cpu.write(0x8c34de28 + index, width, 1)
        cpu.write(0x8c34dbb4 + index, 0, 1)
        if char is not None:
            widths[char] = width
        generated.append(code)

    cpu.stubs.update({0x8c159500: cpu.wait, 0x8c159514: cpu.wait, 0x8c018494: glyph})
    pointer = cpu.read(0x8c13e450)
    for frame in range(20):
        cpu.r[4] = pointer
        cpu.run(BASE + 0x7430, limit=1000000)
        if cpu.r[0] == 1:
            break
    else:
        raise ValueError('Default native cache setup did not finish')
    return cpu, widths, generated, frame + 1


def validate_draw(target, report):
    from validate_vwf import CPU
    template, widths, codes, frames = prepare_native_cache(target)
    texts = [text for _, batch in load_batches(report['version']) for text in batch['translations']]
    required = set(''.join(texts)) - {'\n'}
    missing = sorted(char for char in required if patched_conversion(ord(char)) not in codes)
    # The original converter's ASCII space is deliberately absent; native draw
    # and measure both provide a blank 20-pixel fallback for a missing glyph.
    if missing != [' ']:
        raise ValueError('Default cached font is missing required visible English characters: ' + repr(missing))
    cache_start, cache_end = 0x34d6d0, 0x34e0c0

    def setup():
        cpu = CPU(target)
        cpu.mem[cache_start:cache_end] = template.mem[cache_start:cache_end]
        return cpu

    checked = 0
    for font in (1, 4):
        for binding in report['bindings']:
            cpu = setup()
            cpu.write(0x8c13d75c, font)
            cpu.write_float(0x8c34e0c0, 50.0)
            cpu.write_float(0x8c34e0c4, 50.0)
            cpu.write_float(0x8c34e0c8, 40.0)
            cpu.write_float(0x8c13d758, 1.0)
            cpu.r[4] = BASE + binding['target_file_offset']
            cpu.run(BASE + 0x6090, limit=1000000)
            assert cpu.r[15] == 0x8cf00000
            assert cpu.read_float(0x8c34e0c8) == 40.0 + 22 * (binding['line_count'] - 1)
            checked += 1
        print('Native dispatch checked: {} messages in font mode {}'.format(len(report['bindings']), font), flush=True)
    # Execute the actual prefix -> numeric formatter -> suffix call sequence.
    for count in (3, 38, 100):
        cpu = setup()
        cpu.write(0x8c13d75c, 1)
        cpu.write_float(0x8c34e0c0, 50.0)
        cpu.write_float(0x8c34e0c4, 50.0)
        cpu.write_float(0x8c34e0c8, 40.0)
        cpu.write_float(0x8c13d758, 1.0)
        cpu.r[4] = BASE + report['bindings'][39]['target_file_offset']
        cpu.run(BASE + 0x6090, limit=1000000)
        cpu.r[4], cpu.f[4] = count, -1.0
        cpu.run(BASE + 0x5c1c)
        suffix_offset = report['bindings'][40]['target_file_offset']
        suffix = target[suffix_offset:target.index(b'\x00', suffix_offset)].decode('ascii')
        cpu.r[4] = BASE + suffix_offset
        cpu.run(BASE + 0x6090, limit=1000000)
        expected_x = 50.0 + sum(widths[ord(c)] for c in str(count) + suffix)
        assert cpu.f[0] == expected_x and cpu.read_float(0x8c34e0c8) == 62.0
        assert cpu.r[15] == 0x8cf00000
    composed_cards = 0
    composed_prices = 0
    if len(texts) >= 160:
        # Caller inspection confirms two different destination banks: one-line
        # purchase labels (155-162), and two-line insertion labels (163-170).
        # Exercise both translated and still-Japanese destinations, including
        # row119's second pointer alias, through native string dispatch.
        code_widths = {code: template.read(0x8c34de28 + i, 1) for i, code in enumerate(codes)}

        def line_width(line):
            total = 0
            for char in line:
                encoded = char.encode('cp932')
                code = patched_conversion(encoded[0]) if len(encoded) == 1 else (encoded[0] << 8) | encoded[1]
                total += code_widths.get(code, 20)
            return total

        def draw_parts(pointers):
            cpu = setup()
            cpu.write(0x8c13d75c, 1)
            cpu.write_float(0x8c34e0c0, 50.0)
            cpu.write_float(0x8c34e0c4, 50.0)
            cpu.write_float(0x8c34e0c8, 40.0)
            cpu.write_float(0x8c13d758, 1.0)
            assembled = ''
            for pointer in pointers:
                offset = pointer - BASE
                assembled += target[offset:target.index(b'\x00', offset)].decode('cp932')
                cpu.r[4] = pointer
                cpu.run(BASE + 0x6090, limit=1000000)
            lines = assembled.split('\n')
            assert cpu.read_float(0x8c34e0c8) == 40.0 + 22 * (len(lines) - 1)
            assert cpu.f[0] == 50.0 + line_width(lines[-1])
            assert cpu.r[15] == 0x8cf00000

        for row in (118, 121, 142, 153):
            prefix = BASE + report['bindings'][row - 1]['target_file_offset']
            # Both original absolute references to the shared insertion suffix.
            for destination, suffix_reference in zip((0, 7), report['bindings'][118]['pointer_locations']):
                label = struct.unpack_from('<I', target, 0x12e908 + 4 * destination)[0]
                suffix = struct.unpack_from('<I', target, suffix_reference)[0]
                draw_parts((prefix, label, suffix))
                composed_cards += 1
        for destination in (0, 7):
            label = struct.unpack_from('<I', target, 0x12e8e8 + 4 * destination)[0]
            draw_parts((BASE + report['bindings'][143]['target_file_offset'], label,
                        BASE + report['bindings'][144]['target_file_offset']))
            composed_cards += 1
        for price in (1, 100, 99999):
            cpu = setup()
            cpu.write(0x8c13d75c, 1)
            cpu.write_float(0x8c34e0c0, 50.0)
            cpu.write_float(0x8c34e0c4, 50.0)
            cpu.write_float(0x8c34e0c8, 40.0)
            cpu.write_float(0x8c13d758, 1.0)
            cpu.r[4], cpu.f[4] = price, -1.0
            cpu.run(BASE + 0x5c1c)
            # Currency mode -1 prints only the integer, before row100's unit.
            formatted_price = format(price, ',')
            rendered = bytes(cpu.read(0x8c34e114 + i, 1) for i in range(len(cpu.vertices)))[::-1]
            assert rendered.decode('ascii') == formatted_price
            assert cpu.f[0] == 50.0 + line_width(formatted_price)
            cpu.r[4] = BASE + report['bindings'][99]['target_file_offset']
            cpu.run(BASE + 0x6090, limit=1000000)
            assert cpu.f[0] == 50.0 + line_width(texts[99].split('\n')[-1])
            assert cpu.read_float(0x8c34e0c8) == 62.0 and cpu.r[15] == 0x8cf00000
            composed_prices += 1
    return {'actual_machine_code_draw_cases': checked, 'fonts': [1, 4],
            'composed_block_warning_cases': 3,
            'composed_memory_card_cases': composed_cards, 'composed_price_cases': composed_prices,
            'default_native_cache_frames': frames, 'default_native_cache_glyphs': len(codes),
            'required_visible_characters_loaded': len(required) - 1,
            'space_behavior': 'Original cache-miss blank fallback, 20 pixels in both draw and measure',
            'synthetic_cache': True, 'emulator_playtest': False,
            'validated': ['Every translated target read back through each original pointer',
                          'Only intended VWF, bank and pointer bytes changed',
                          'Newline/control-token preservation', 'Native string dispatch and stack preservation']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default=VERSION, choices=sorted(RELEASE_BATCHES))
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--build', action='store_true')
    actions.add_argument('--verify-existing', action='store_true', help='Read back the existing build without changing tracks')
    actions.add_argument('--plan-only', action='store_true', help='Inspect bindings and samples without running native drawing checks')
    parser.add_argument('--report', action='store_true', help='Save updated validation evidence with --verify-existing')
    args = parser.parse_args()
    if args.report and not args.verify_existing:
        raise ValueError('--report requires --verify-existing')
    disc = Disc()
    entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
    original = disc.read(entry['lba'], entry['size'])
    version = args.version
    batches = load_batches(version)
    target, report = plan(original, version)
    folder = ROOT / 'work' / 'output' / ('english-' + version)
    previous_report = folder / 'PATCH-REPORT.json'
    # Track verification checks the exact planned bytes. Reuse the native-code
    # evidence for that same program instead of rerunning unchanged draw cases.
    if args.verify_existing and previous_report.is_file():
        previous = json.loads(previous_report.read_text(encoding='utf-8'))
        matching_batches = previous.get('batches') == report['batches']
        if version == '0.1.2' and 'batches' not in previous:
            matching_batches = previous.get('batch_source_sha256') == report['batches'][0]['sha256']
        if (previous['target_program_sha256'] != report['target_program_sha256']
                or not matching_batches):
            raise ValueError('Existing build does not match this translation revision')
        report['validation'] = previous['validation']
    elif not args.plan_only:
        report['validation'] = validate_draw(target, report)
    print(json.dumps({key: value for key, value in report.items() if key not in ('bindings', 'vwf')}, indent=2))
    texts = [text for _, batch in batches for text in batch['translations']]
    for binding in report['bindings'][-80:-77]:
        print('Sample:', binding['id'], '=>', repr(texts[binding['row'] - 1]))
    if args.verify_existing:
        track = next(folder.glob('*.bin'))
        track_start, _, source_track = next(t for t in disc.tracks if t[0] <= entry['lba'] < t[1])
        source_raw, raw = source_track.read_bytes(), track.read_bytes()
        if len(source_raw) != len(raw):
            raise ValueError('Patched track size changed')
        changes = []
        for index in range(len(raw) // 2352):
            before, after = source_raw[index * 2352:(index + 1) * 2352], raw[index * 2352:(index + 1) * 2352]
            if before == after:
                continue
            lba = track_start + index
            file_sector = lba - entry['lba']
            if not 0 <= file_sector < (len(target) + 2047) // 2048:
                raise ValueError('Track changed outside the executable')
            offset = file_sector * 2048
            replacement = target[offset:offset + 2048]
            expected_user = replacement + before[16 + len(replacement):2064]
            if before[:16] != after[:16] or regenerate(after) != after or after[16:2064] != expected_user:
                raise ValueError('Patched sector differs from the intended executable or EDC/ECC')
            changes.append({'lba': lba, 'track_offset': index * 2352})
        position = (entry['lba'] - track_start) * 2352
        payload = b''.join(raw[p + 16:p + 2064] for p in range(position, position + ((len(target) + 2047) // 2048) * 2352, 2352))[:len(target)]
        if payload != target:
            raise ValueError('Executable read-back mismatch')
        descriptor = next(folder.glob('*.gdi')).read_text(encoding='utf-8').splitlines()
        assert int(descriptor[0]) == 17 and len(descriptor) == 18
        for number, line in enumerate(descriptor[1:], 1):
            fields = shlex.split(line)
            expected_track = track if number == 17 else next(ROOT.glob('*Track {:02d}*.bin'.format(number)))
            assert (folder / fields[4]).resolve() == expected_track.resolve() and expected_track.is_file()
            assert int(fields[0]) == number and int(fields[3]) == 2352
            assert int(fields[2]) == (4 if number in (1, 3, 17) else 0)
            skip = (0 if number in (1, 3) else 225 if number == 17 else 150) * 2352
            assert int(fields[5]) == skip
            if number >= 3:
                original_track = next(ROOT.glob('*Track {:02d}*.bin'.format(number)))
                lba_start = next(t[0] for t in disc.tracks if t[2] == original_track)
                assert int(fields[1]) == lba_start + skip // 2352
        report['modified_sectors'] = changes
        report['source_track_sha256'], report['target_track_sha256'] = digest(source_raw), digest(raw)
        report['validation']['built_track_verified'] = True
        report['validation']['gdi_tracks_verified'] = 17
        print('Existing build verified:', len(changes), 'changed sectors; all other track bytes unchanged; 17 GDI references verified.')
        if args.report:
            for path in (folder / 'PATCH-REPORT.json', inventory_path(version)):
                path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        return
    if not args.build:
        print('Dry run only; no disc or reports written.')
        return
    if any(batch['status'] != 'meaning_reviewed_pending_ui_playtest' for _, batch in batches):
        raise ValueError('Complete meaning review before creating a test build')
    folder.mkdir(parents=True, exist_ok=False)
    track = folder / ('Marionette Handler 2 (Japan) (Track 17) English ' + version + '.bin')
    report['modified_sectors'] = write_track(disc, entry, original, target, track)
    # Read back the complete executable payload from the generated raw track.
    track_start = next(t[0] for t in disc.tracks if t[0] <= entry['lba'] < t[1])
    raw = track.read_bytes()
    position = (entry['lba'] - track_start) * 2352
    payload = b''.join(raw[p + 16:p + 2064] for p in range(position, position + ((len(target) + 2047) // 2048) * 2352, 2352))[:len(target)]
    if payload != target:
        raise ValueError('Patched executable read-back failed')
    report['target_track_sha256'] = digest(raw)
    name = 'Marionette Handler 2 English ' + version
    gdi(disc, track, folder / (name + '.gdi'))
    cue = next(ROOT.glob('*.cue')).read_text(encoding='utf-8')
    for source in sorted(ROOT.glob('*Track*.bin')):
        path = track if '(Track 17)' in source.name else source
        filename = Path(os.path.relpath(str(path), str(folder))).as_posix()
        cue = cue.replace('"' + source.name + '"', '"' + filename + '"')
    (folder / (name + '.cue')).write_text(cue, encoding='utf-8')
    for path in (folder / 'PATCH-REPORT.json', inventory_path(version)):
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('English test build:', folder)


if __name__ == '__main__':
    main()
