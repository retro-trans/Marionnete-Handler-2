"""Build all 793 reviewed English game records; --plan-only never writes files."""
import argparse
import json
import os
from pathlib import Path
import shlex
import struct

from inspect_disc_text import Disc, ROOT
from full_english import VERSION, BASE, FIXED, batches, conversion, digest, plan
from build_english import prepare_native_cache
from build_vwf import write_track, gdi, WIDTH_TABLE
from cdrom_sector import regenerate
from validate_vwf import CPU


def validate(original, target, report, cache_metrics=None):
    _, texts, _ = batches()
    # Execute the actual startup clear/copy routine, not a predicted interval.
    startup = CPU(target)
    startup.run(BASE + 0x141c64, limit=5000000)
    for a, z in report['changed_regions']:
        assert startup.mem[0x10000 + a:0x10000 + z] == target[a:z]
    template, _, codes, frames = prepare_native_cache(target)
    if cache_metrics is not None:
        for i,code in enumerate(codes):
            bearing,advance=cache_metrics[code]
            template.write(0x8c34dbb4+i,bearing,1)
            template.write(0x8c34de28+i,advance,1)
    code_widths = {code: template.read(0x8c34de28 + i, 1) for i, code in enumerate(codes)}
    import re
    printable = set(''.join(re.sub(r'@[a-zA-Z]\d{3}', '', text) for text in texts)) - {'\n'}
    missing = sorted(c for c in printable if conversion(ord(c)) not in codes)
    assert missing == [' '], ('Missing visible glyphs', missing)

    def setup(font=1):
        cpu = CPU(target)
        cpu.mem[0x34d6d0:0x34e0c0] = template.mem[0x34d6d0:0x34e0c0]
        cpu.write(0x8c13d75c, font)
        cpu.write_float(0x8c34e0c0, 50.0)
        cpu.write_float(0x8c34e0c4, 50.0)
        cpu.write_float(0x8c34e0c8, 40.0)
        cpu.write_float(0x8c13d758, 1.0)
        cpu.f[4] = 400.0
        return cpu

    def pointer(binding):
        if binding['row'] <= 560:
            return struct.unpack_from('<I', target, binding['pointer_locations'][0])[0]
        return BASE + binding['source_file_offset']

    resolver_cases = 0
    for binding in report['bindings']:
        if binding['row'] <= 560 or binding['category'] in FIXED:
            continue
        cpu = setup()
        cpu.r[4] = BASE + binding['source_file_offset']
        cpu.run(report['resolver']['entry'], limit=10000)
        assert cpu.r[4] == BASE + binding['target_file_offset'] and cpu.r[15] == 0x8cf00000
        resolver_cases += 1
    # Copied name handles are checked through the real library's 17-word loop.
    copies = 0
    for binding in report['bindings']:
        if binding['storage'] != 'copiable_name_handle':
            continue
        cpu = setup()
        source = BASE + binding['source_file_offset']
        cpu.r[4], cpu.r[5], cpu.r[6] = 0x8ce00000, source, 17
        cpu.run(BASE + 0x1612dc)
        assert cpu.mem[0xe00000:0xe00044] == target[binding['source_file_offset']:binding['source_file_offset'] + 68]
        assert cpu.mem[0xe00020:0xe00044] == original[binding['source_file_offset'] + 32:binding['source_file_offset'] + 68]
        cpu.r[4] = 0x8ce00000
        cpu.run(report['resolver']['entry'], limit=10000)
        assert cpu.r[4] == BASE + binding['target_file_offset']
        copies += 1
    for index, binding in enumerate(report['bindings'], 1):
        cpu = setup()
        cpu.r[4] = pointer(binding)
        saved = cpu.r[8:15].copy()
        cpu.run(BASE + 0x6090, limit=3000000)
        assert cpu.r[15] == 0x8cf00000 and cpu.r[8:15] == saved
        assert cpu.read_float(0x8c34e0c8) == 40.0 + 22 * (binding['line_count'] - 1)
        if index % 80 == 0 or index == len(texts):
            print('Native message dispatch:', index, '/', len(texts), flush=True)
    measured = 0
    aligned = 0
    for binding in report['bindings'][560:]:
        text = texts[binding['row'] - 1]
        cpu = setup()
        cpu.r[4] = pointer(binding)
        cpu.run(BASE + 0x63e4, limit=3000000)
        expected = sum(code_widths.get(conversion(ord(c)), 20) for c in text.split('\n')[0])
        assert cpu.f[0] == float(expected) and cpu.r[15] == 0x8cf00000
        measured += 1
        if 698 <= binding['row'] <= 740 or 754 <= binding['row'] <= 766:
            via_old, direct = setup(), setup()
            via_old.r[4] = pointer(binding)
            direct.r[4] = BASE + binding['target_file_offset']
            via_old.run(BASE + 0x6460, limit=3000000)
            direct.run(BASE + 0x6460, limit=3000000)
            assert via_old.f[0] == direct.f[0] and via_old.vertices == direct.vertices
            assert via_old.r[15] == direct.r[15] == 0x8cf00000
            aligned += 1
    def composed(parts):
        cpu = setup()
        for kind, value in parts:
            if kind == 'number':
                cpu.r[4], cpu.f[4] = value, -1.0
                cpu.run(BASE + 0x5c1c)
            else:
                cpu.r[4] = pointer(report['bindings'][value - 1])
                cpu.run(BASE + 0x6090, limit=3000000)
        assert cpu.r[15] == 0x8cf00000
        return cpu
    def advance(text):
        return sum(code_widths.get(conversion(ord(c)), 20) for c in text)
    numeric = 0
    for n in (1, 30, 100):
        cases = (((('text', 747), ('number', n), ('text', 748)), 'Match ' + str(n)),
                 ((('number', n), ('text', 751)), str(n) + ' steps'),
                 ((('number', 2), ('text', 789), ('number', n), ('text', 790), ('text', 114)), '2 hr ' + str(n) + ' min elapsed.'),
                 ((('number', 12), ('text', 793), ('number', n), ('text', 790), ('text', 115)), '12 h ' + str(n) + ' min has been reached.'))
        for parts, expected in cases:
            cpu = composed(parts)
            assert cpu.f[0] == 50.0 + advance(expected)
            numeric += 1
    # Real timer code uses positive field widths: preserve those formatter modes.
    for hour_row in (789, 793):
        cpu = setup()
        for n, mode, row in ((2 if hour_row == 789 else 12, 20.0, hour_row), (30, 40.0, 790)):
            cpu.r[4], cpu.f[4] = n, mode
            cpu.run(BASE + 0x5c1c)
            before = cpu.f[0]
            cpu.r[4] = pointer(report['bindings'][row - 1])
            cpu.run(BASE + 0x6090, limit=3000000)
            assert cpu.f[0] == before + advance(texts[row - 1])
        numeric += 1
    for binding, text in zip(report['bindings'], texts):
        binding['visible_line_characters'] = [len(re.sub(r'@[a-zA-Z]\d{3}', '', line)) for line in text.split('\n')]
        binding['small_font_line_widths_px'] = [sum(target[WIDTH_TABLE + ord(c) - 32] + 2 for c in re.sub(r'@[a-zA-Z]\d{3}', '', line)) for line in text.split('\n')]
    return {'native_startup_clear_verified': True, 'native_message_dispatch_cases': len(texts),
            'supplemental_address_resolution_cases': resolver_cases, 'copied_tournament_record_cases': copies,
            'native_width_measure_cases': measured, 'native_aligned_render_equivalence_cases': aligned,
            'numeric_composition_cases': numeric, 'default_native_cache_glyphs': len(codes),
            'default_native_cache_frames': frames, 'visible_english_characters_loaded': len(printable) - 1,
            'space_behavior': 'Original blank 20-pixel cache-miss fallback',
            'bios_ink_metrics_simulated': cache_metrics is None, 'emulator_playtest': False,
            'approved_screen_fit_limits': None}


def verify_track(disc, entry, original, target, report, folder):
    track = next(folder.glob('*.bin'))
    track_start, _, source = next(t for t in disc.tracks if t[0] <= entry['lba'] < t[1])
    before, after = source.read_bytes(), track.read_bytes()
    assert len(before) == len(after)
    edited = []
    for index in range(len(after) // 2352):
        a, b = before[index * 2352:(index + 1) * 2352], after[index * 2352:(index + 1) * 2352]
        if a == b:
            continue
        sector = track_start + index - entry['lba']
        assert 0 <= sector < (len(target) + 2047) // 2048
        blob = target[sector * 2048:(sector + 1) * 2048]
        assert b[:16] == a[:16] and regenerate(b) == b
        assert b[16:2064] == blob + a[16 + len(blob):2064]
        edited.append({'lba': track_start + index, 'track_offset': index * 2352})
    start = (entry['lba'] - track_start) * 2352
    payload = b''.join(after[p + 16:p + 2064] for p in range(start, start + ((len(target) + 2047) // 2048) * 2352, 2352))[:len(target)]
    assert payload == target
    descriptor = next(folder.glob('*.gdi')).read_text(encoding='utf-8').splitlines()
    assert descriptor[0] == '17' and len(descriptor) == 18
    for number, line in enumerate(descriptor[1:], 1):
        fields = shlex.split(line)
        expected = track if number == 17 else next(ROOT.glob('*Track {:02d}*.bin'.format(number)))
        assert (folder / fields[4]).resolve() == expected.resolve()
        assert int(fields[0]) == number and int(fields[3]) == 2352
        assert int(fields[2]) == (4 if number in (1, 3, 17) else 0)
        skip = (0 if number in (1, 3) else 225 if number == 17 else 150) * 2352
        assert int(fields[5]) == skip
        if number >= 3:
            source_track = next(ROOT.glob('*Track {:02d}*.bin'.format(number)))
            assert int(fields[1]) == next(t[0] for t in disc.tracks if t[2] == source_track) + skip // 2352
    report.update(modified_sectors=edited, source_track_sha256=digest(before), target_track_sha256=digest(after))
    report['validation'].update(built_track_verified=True, gdi_tracks_verified=17)
    print('Full track verified:', len(edited), 'edited sectors, all other bytes unchanged, 17 GDI references.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--plan-only', action='store_true')
    group.add_argument('--build', action='store_true')
    group.add_argument('--verify-existing', action='store_true')
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    if args.report and not args.verify_existing:
        raise ValueError('--report requires --verify-existing')
    disc = Disc()
    entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
    original = disc.read(entry['lba'], entry['size'])
    target, report = plan(original)
    folder = ROOT / 'work/output' / ('english-' + VERSION)
    if args.verify_existing:
        previous = json.loads((folder / 'PATCH-REPORT.json').read_text(encoding='utf-8'))
        assert previous['target_program_sha256'] == report['target_program_sha256'] and previous['batches'] == report['batches']
        report['validation'] = previous['validation']
        # Keep measured evidence bound to the exact tested strings.
        for binding, old in zip(report['bindings'], previous['bindings']):
            for key in ('visible_line_characters', 'small_font_line_widths_px'):
                binding[key] = old[key]
        verify_track(disc, entry, original, target, report, folder)
    elif not args.plan_only:
        report['validation'] = validate(original, target, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('bindings', 'changed_regions', 'batches')}, indent=2))
    for number in (175, 561, 676, 747, 751, 789):
        b = report['bindings'][number - 1]
        at = b['target_file_offset']
        print('Sample', number, repr(target[at:target.index(b'\x00', at)].decode('ascii')))
    if args.build:
        folder.mkdir(parents=True, exist_ok=False)
        track = folder / ('Marionette Handler 2 (Japan) (Track 17) English ' + VERSION + '.bin')
        write_track(disc, entry, original, target, track)
        name = 'Marionette Handler 2 English ' + VERSION
        gdi(disc, track, folder / (name + '.gdi'))
        cue = next(ROOT.glob('*.cue')).read_text(encoding='utf-8')
        for source in sorted(ROOT.glob('*Track*.bin')):
            relative = Path(os.path.relpath(str(track if '(Track 17)' in source.name else source), str(folder))).as_posix()
            cue = cue.replace('"' + source.name + '"', '"' + relative + '"')
        (folder / (name + '.cue')).write_text(cue, encoding='utf-8')
        verify_track(disc, entry, original, target, report, folder)
    if args.build or args.report:
        for path in (folder / 'PATCH-REPORT.json', ROOT / 'work/ui/english_0.1.4_inventory.json'):
            path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('English test release:', folder)
    elif not args.verify_existing:
        print('Dry run only; no image or reports written.')


if __name__ == '__main__':
    main()
