"""Read-only disc inventory and conservative CP932 text discovery.

The source image is never modified. Full Japanese scripts are not exported.
Run without --report first to review candidate counts and short samples.
"""
import argparse
import bisect
import collections
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
SYNC = b'\x00' + b'\xff' * 10 + b'\x00'


class Disc:
    def __init__(self, root=ROOT):
        self.tracks = []
        lba = 45000
        for path in sorted(root.glob('*Track*.bin')):
            number = int(re.search(r'Track (\d+)', path.name).group(1))
            if number < 3:
                continue
            sectors = path.stat().st_size // 2352
            self.tracks.append((lba, lba + sectors, path))
            lba += sectors
        self.starts = [t[0] for t in self.tracks]
        pvd = self.read(45016, 2048)
        if pvd[:7] != b'\x01CD001\x01':
            raise ValueError('Unexpected primary volume descriptor')
        self.volume = pvd[40:72].decode('ascii').strip()
        self.files = list(self.walk(int.from_bytes(pvd[158:162], 'little'),
                                    int.from_bytes(pvd[166:170], 'little')))

    def read(self, lba, size):
        chunks = []
        remaining = (size + 2047) // 2048
        while remaining:
            index = bisect.bisect_right(self.starts, lba) - 1
            start, end, path = self.tracks[index]
            if not start <= lba < end:
                raise ValueError('LBA outside source tracks: {}'.format(lba))
            count = min(remaining, end - lba)
            with path.open('rb') as f:
                f.seek((lba - start) * 2352)
                raw = f.read(count * 2352)
            for offset in range(0, len(raw), 2352):
                sector = raw[offset:offset + 2352]
                if sector[:12] != SYNC or sector[15] != 1:
                    raise ValueError('Expected MODE1 sector at LBA {}'.format(lba + offset // 2352))
                chunks.append(sector[16:2064])
            remaining -= count
            lba += count
        return b''.join(chunks)[:size]

    def walk(self, lba, size, parent=''):
        data = self.read(lba, size)
        offset = 0
        while offset < len(data):
            length = data[offset]
            if not length:
                offset = (offset // 2048 + 1) * 2048
                continue
            record = data[offset:offset + length]
            offset += length
            name = record[33:33 + record[32]]
            if name in (b'\x00', b'\x01'):
                continue
            path = parent + '/' + name.decode('ascii').split(';')[0]
            loc = int.from_bytes(record[2:6], 'little')
            length = int.from_bytes(record[10:14], 'little')
            if record[25] & 2:
                for entry in self.walk(loc, length, path):
                    yield entry
            else:
                yield {'path': path, 'lba': loc, 'size': length}


# Strictly encoded runs; these are candidates, not automatically real UI text.
RUN = re.compile(rb'(?:[\x20-\x7e\xa1-\xdf]|[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc])+')
JP = re.compile('[\u3040-\u30ff\u3400-\u9fff]')
KANA = re.compile('[\u3040-\u30ff]')


def candidates(data):
    for match in RUN.finditer(data):
        raw = match.group()
        try:
            value = raw.decode('cp932')
        except UnicodeDecodeError:
            continue
        jp = len(JP.findall(value))
        kana = len(KANA.findall(value))
        if jp < 2 or jp / max(1, len(value)) < 0.4 or kana < 1:
            continue
        yield {'offset': match.start(), 'length': len(raw), 'text': value,
               'null_terminated': data[match.end():match.end() + 1] == b'\x00',
               'preceded_by_null': match.start() == 0 or data[match.start() - 1] == 0}


def reviewed_inventory(disc):
    """Reviewed text areas for this source revision, with binary floats excluded.

    Records are translation units, not individual display lines. No source text
    is persisted. Exact byte hashes let a later translator re-read the image.
    """
    entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
    data = disc.read(entry['lba'], entry['size'])
    refs = collections.defaultdict(list)
    for off in range(0, len(data) - 3, 4):
        target = struct.unpack_from('<I', data, off)[0] - 0x8c010000
        if 0 <= target < len(data):
            refs[target].append(off)
    units = []
    texts = []

    def add(offset, raw, category, file_entry=entry, message_id=None):
        value = raw.decode('cp932')
        if not JP.search(value):
            return
        digest = hashlib.sha256(raw).hexdigest()
        record = {'id': '{}:{:08x}'.format(file_entry['path'], offset),
                  'file': file_entry['path'], 'category': category,
                  'file_offset': offset, 'source_bytes': len(raw),
                  'source_characters': len(value), 'source_sha256': digest,
                  'encoding': 'cp932', 'line_count': value.count('\n') + 1}
        if message_id is None:
            record['terminator'] = '00'
            record['absolute_pointer_locations'] = refs[offset]
        else:
            record['message_id'] = message_id
        units.append(record)
        texts.append(value)

    # Fixed-size records: tournament titles, consumables, equipment presets.
    for start, stride, count, category in (
        (0x8af4c, 0x44, 28, 'tournament_titles'),
        (0x8d020, 0x3c, 13, 'consumable_names'),
        (0x8d368, 0x38, 56, 'equipment_preset_names'),
    ):
        for i in range(count):
            offset = start + stride * i
            end = data.index(b'\x00', offset, offset + stride)
            add(offset, data[offset:end], category)

    # Interleaved pools include some pointer tables and numeric data. The two
    # floating-point fragments below decode as Japanese by chance, not text.
    excluded = {0x12dde2, 0x12de02}
    for start, end, category in (
        (0x12daac, 0x12e415, 'training_and_programming_labels'),
        (0x130097, 0x136e36, 'menus_prompts_help_and_descriptions'),
        (0x139310, 0x1393a0, 'battle_results_labels'),
        (0x13c53e, 0x13cd02, 'equipment_stats_and_customization'),
    ):
        for match in re.finditer(rb'[^\x00]+', data[start:end]):
            offset = start + match.start()
            if offset in excluded:
                continue
            raw = match.group()
            try:
                value = raw.decode('cp932')
            except UnicodeDecodeError:
                continue
            if any(ord(c) < 32 and c not in '\r\n\t' for c in value):
                continue
            if any(0x7f <= ord(c) <= 0x9f or 0xe000 <= ord(c) <= 0xf8ff for c in value):
                continue
            add(offset, raw, category)

    core_count = len(units)
    core_unique = len(set(texts))
    message_entry = next(e for e in disc.files if e['path'] == '/DPETC/MESSAGE.INI')
    messages = disc.read(message_entry['lba'], message_entry['size'])
    assignments = list(re.finditer(rb'^(\d+)\s*=\s*"(.*?)"\s*(?:\r?\n|$)', messages, re.M | re.S))
    expected = re.findall(rb'^\d+\s*=', messages, re.M)
    if len(assignments) != len(expected):
        raise ValueError('Message parser missed an assignment')
    for match in assignments:
        add(match.start(2), match.group(2), 'network_browser_messages',
            message_entry, int(match.group(1)))
    network_texts = texts[core_count:]
    category_counts = dict(sorted(collections.Counter(u['category'] for u in units).items()))
    texture_files = [e for e in disc.files if Path(e['path']).suffix.upper() in ('.PVR', '.PVM')]
    return {
        'assessment_version': '0.1.0', 'assessment_date': '2026-10-01',
        'volume': disc.volume, 'disc_files': len(disc.files),
        'source_program_sha256': hashlib.sha256(data).hexdigest(),
        'source_messages_sha256': hashlib.sha256(messages).hexdigest(),
        'counts': {'game_text_entries': core_count, 'game_text_unique_exact': core_unique,
                   'network_message_entries': len(network_texts),
                   'network_messages_unique_exact': len(set(network_texts)),
                   'total_entries': len(units), 'total_unique_exact': len(set(texts)),
                   'categories': category_counts, 'texture_files_not_text_counted': len(texture_files)},
        'method': 'Reviewed CP932 NUL-terminated string pools and fixed-stride tables; numeric INI assignments. Newlines remain within their original entry. Exact string deduplication only.',
        'limitations': ['Lower bound, not a complete in-game UI census.',
                        'Text in textures, browser executable and page scripts is not included.',
                        'No emulator verification, translation, patched build, or Retro Trans Tools compatibility test has been performed.',
                        'Source byte length is descriptive; it is not an approved translation byte budget.',
                        'Inline formatting codes and runtime references require preservation during translation.'],
        'entries': units,
        'files': disc.files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true', help='Save source-free discovery metadata')
    parser.add_argument('--samples', type=int, default=5, help='Maximum short samples per file')
    parser.add_argument('--reviewed', action='store_true', help='Use reviewed game text areas and numeric browser messages')
    args = parser.parse_args()
    disc = Disc()
    if args.reviewed:
        report = reviewed_inventory(disc)
        print(json.dumps(report['counts'], indent=2))
        if args.report:
            path = ROOT / 'work' / 'ui' / 'text_inventory.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2), encoding='utf-8')
            print('Saved:', path)
        return
    summaries = []
    print('Volume:', disc.volume, '| Files:', len(disc.files))
    for entry in disc.files:
        if Path(entry['path']).suffix.upper() not in ('.BIN', '.MAO', '.PRG', '.INI', '.DPS', '.TXT', '.HTML'):
            continue
        data = disc.read(entry['lba'], entry['size'])
        rows = list(candidates(data))
        if not rows:
            continue
        count = len(rows)
        unique = len(set(r['text'] for r in rows))
        nulls = sum(r['null_terminated'] for r in rows)
        print('{}: {} candidates, {} unique, {} null-terminated'.format(entry['path'], count, unique, nulls))
        samples = [r for r in rows if r['null_terminated'] and len(r['text']) <= 30]
        for r in samples[:args.samples]:
            print('  0x{:x}: {}'.format(r['offset'], r['text'].encode('ascii', 'backslashreplace').decode()))
        summaries.append(dict(entry, candidate_occurrences=count, candidate_unique=unique,
                              null_terminated_candidates=nulls,
                              strings=[{k: v for k, v in dict(r, source_sha256=hashlib.sha256(r['text'].encode('utf-8')).hexdigest()).items() if k != 'text'} for r in rows]))
    if args.report:
        path = ROOT / 'work' / 'ui' / 'text_discovery.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'assessment_version': '0.1.0', 'volume': disc.volume,
                                    'method': 'Heuristic CP932 runs; counts require review; no source scripts exported',
                                    'files': disc.files, 'text_candidates': summaries}, indent=2), encoding='utf-8')
        print('Saved:', path)


if __name__ == '__main__':
    main()
