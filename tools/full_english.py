"""Plan all 793 English records with native display indirection, without disc writes."""
import hashlib
import bisect
import json
import re
import struct

from inspect_disc_text import ROOT
from game_text_rows import game_rows
from build_vwf import BASE, SOURCE_SHA256, CONVERTER_START, patched_conversion, plan as vwf_plan
from sh4_patch import Assembler, pc_load

VERSION = '0.1.4'
TAIL_START = 0x1928a4
CODE_START, CODE_END = 0x7de4, 0x7f64
FIXED = {'tournament_titles', 'consumable_names', 'equipment_preset_names'}
BRACKETS = {91: 0x816d, 93: 0x816e}


def conversion(char):
    return BRACKETS.get(char, patched_conversion(char))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def batches():
    files = list((ROOT / 'work/translation/en').glob('*batch_*.json'))
    loaded = [(path, json.loads(path.read_text(encoding='utf-8'))) for path in files]
    loaded.sort(key=lambda item: item[1]['slice']['first_row'])
    cursor = 1
    texts, notes = [], {}
    for path, batch in loaded:
        count = len(batch['translations'])
        if (batch['slice']['first_row'] != cursor or batch['slice']['last_row'] != cursor + count - 1
                or count != (73 if cursor == 721 else 80) or batch['language'] != 'en'
                or batch['source_program_sha256'] != SOURCE_SHA256
                or batch['status'] != 'meaning_reviewed_pending_ui_playtest'):
            raise ValueError('Incomplete/reordered/unreviewed batch: ' + path.name)
        texts.extend(batch['translations'])
        notes.update(batch.get('notes', {}))
        cursor += count
    if len(texts) != 793:
        raise ValueError('Expected all 793 translations')
    return loaded, texts, notes


def resolver(address, table, count, marker_table, marker_count):
    a = Assembler(address)
    a.load(1, table)
    a.load(2, count)
    a.label('lookup')
    a.emit(0x6016, 0x3040)  # mov.l @r1+,r0; cmp/eq r4,r0 (odd values retained)
    a.branch(0x8900, 'found')
    a.emit(0x7104, 0x72ff, 0x2228)
    a.branch(0x8b00, 'lookup')
    # Fixed-record name handles survive the native 68-byte tournament copy.
    # Exact @EA .. @EF + NUL are reserved internal display handles.
    a.emit(0x6143, 0x6014, 0x600c, 0x8840)
    a.branch(0x8b00, 'unchanged')
    a.emit(0x6014, 0x600c, 0x8845)
    a.branch(0x8b00, 'unchanged')
    a.emit(0x6014, 0x600c, 0x70bf)
    a.load(2, marker_count)
    a.emit(0x3022)
    a.branch(0x8900, 'unchanged')
    a.emit(0x6310, 0x2338)
    a.branch(0x8b00, 'unchanged')
    a.emit(0x4008)
    a.load(1, marker_table)
    a.emit(0x041e, 0x000b, 0x0009)
    a.label('found')
    a.emit(0x6412, 0x000b, 0x0009)
    a.label('unchanged')
    a.emit(0x000b, 0x0009)
    return a.finish()


def trampoline(address, resolve, original_prologue, continuation):
    a = Assembler(address)
    a.emit(0x4f22, 0x2f16, 0x2f26, 0x2f36)
    a.load(0, resolve)
    a.emit(0x400b, 0x0009, 0x63f6, 0x62f6, 0x61f6, 0x4f26)
    a.emit(*struct.unpack('<{}H'.format(len(original_prologue) // 2), original_prologue))
    a.load(0, continuation)
    a.emit(0x402b, 0x0009)
    return a.finish()


def merged(spans):
    result = []
    for start, end in sorted(spans):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def plan(original):
    loaded, texts, notes = batches()
    rows = game_rows()
    gloss = json.loads((ROOT / 'work/glossary/en.json').read_text(encoding='utf-8'))
    source_starts = {BASE + row['file_offset'] for row in rows}
    spans = sorted((row['file_offset'], row['file_offset'] + row['source_bytes'] + 1) for row in rows)
    span_starts = [start for start, _ in spans]
    for offset in range(0, len(original) - 3, 4):
        pointer = struct.unpack_from('<I', original, offset)[0]
        if pointer in source_starts:
            continue
        local = pointer - BASE
        index = bisect.bisect_right(span_starts, local) - 1
        if index >= 0 and spans[index][0] < local < spans[index][1]:
            raise ValueError('Unreviewed interior source pointer at 0x{:x} -> 0x{:x}'.format(offset, local))
    patched, vwf = vwf_plan(original)
    patched = bytearray(patched)
    changes = [(c['file_offset'], c['file_offset'] + c['bytes']) for c in vwf['changes']]
    bindings, pool, markers, tasks = [], [], [], []
    for ordinal, (row, text) in enumerate(zip(rows, texts), 1):
        start = row['file_offset']
        raw = original[start:start + row['source_bytes']]
        source = raw.decode('cp932')
        if digest(raw) != row['source_sha256'] or original[start + len(raw)] != 0:
            raise ValueError('Source revision mismatch at row ' + str(ordinal))
        target = text.encode('ascii')
        if any(byte != 10 and not 32 <= byte <= 126 for byte in target):
            raise ValueError('Unsupported ASCII/control at row ' + str(ordinal))
        if source.count('\n') != text.count('\n'):
            raise ValueError('Unreviewed newline change at row ' + str(ordinal))
        controls = r'@[a-zA-Z]\d{3}|%[-+ #0]*\d*(?:\.\d+)?[diuoxXfFeEgGcs]|\\[nrt]'
        if re.findall(controls, source) != re.findall(controls, text):
            raise ValueError('Control token mismatch at row ' + str(ordinal))
        for term in gloss['terms']:
            if term['source'] in source:
                allowed = [term['target'], term.get('plural', term['target']), term.get('adjective', term['target'])]
                if not any(word.casefold() in text.casefold() for word in allowed):
                    raise ValueError('Glossary mismatch row {}: {}'.format(ordinal, term['target']))
        binding = {'row': ordinal, 'id': row['id'], 'category': row['category'],
                   'source_file_offset': start, 'source_sha256': digest(raw),
                   'target_bytes': len(target), 'target_sha256': digest(target),
                   'line_count': text.count('\n') + 1, 'review_note': notes.get(str(ordinal))}
        bindings.append(binding)
        if row['category'] in FIXED:
            if any(original[start + len(raw) + 1:start + 32]):
                raise ValueError('Name padding is not zero: ' + row['id'])
            if len(target) < 32:
                compiled = target + b'\x00'
                binding.update(target_file_offset=start, storage='native_32_byte_name_field')
            else:
                marker = b'@E' + bytes([65 + len(markers)]) + b'\x00'
                markers.append(ordinal)
                compiled = marker
                binding.update(storage='copiable_name_handle', handle=marker[:-1].decode('ascii'))
                tasks.append((ordinal, target + b'\x00'))
            patched[start:start + 32] = compiled + b'\x00' * (32 - len(compiled))
            changes.append((start, start + 32))
            pool.append((start + len(compiled), start + 32))
        else:
            pool.append((start, start + len(raw) + 1))
            tasks.append((ordinal, target + b'\x00'))
    # Leave relative/base-derived supplemental pointers unchanged; map all 137.
    mapped = [b for b in bindings if b['row'] > 560 and b['category'] not in FIXED]
    keys = {b['source_file_offset'] for b in mapped}
    if any(original[TAIL_START:]):
        raise ValueError('Expected initialized zero tail before the BSS boundary')
    for offset in range(0, len(original) - 3, 4):
        value = struct.unpack_from('<I', original, offset)[0] - BASE
        if TAIL_START <= value < len(original):
            raise ValueError('Executable tail contains a referenced object')
    map_start = TAIL_START
    marker_start = map_start + 8 * len(mapped)
    table_end = marker_start + 4 * len(markers)
    code = resolver(BASE + CODE_START, BASE + map_start, len(mapped), BASE + marker_start, len(markers))
    resolve = BASE + CODE_START
    hooks = []
    for entry, prologue, continuation in ((0x6090, original[0x6090:0x609c], 0x609c),
                                          (0x63e4, original[0x63e4:0x63ec] + struct.pack('<H', 0xff8d), 0x6438),
                                          (0x6460, original[0x6460:0x646c], 0x646c)):
        address = BASE + CODE_START + len(code)
        code += trampoline(address, resolve, prologue, BASE + continuation)
        replacement = struct.pack('<4HI', pc_load(0, BASE + entry, BASE + entry + 8), 0x402b, 0x0009, 0x0009, address)
        patched[entry:entry + 12] = replacement
        changes.append((entry, entry + 12))
        hooks.append({'entry': entry, 'trampoline': address, 'continuation': continuation})
    if len(code) > CODE_END - CODE_START or table_end > len(original):
        raise ValueError('Resolver exceeds verified reclaimed space')
    # Old fixed renderer has no remaining callers after VWF: only three source
    # literal references exist and all three are redirected by the VWF patch.
    old_renderer = struct.pack('<I', BASE + CODE_START)
    old_refs = [i for i in range(len(original) - 3) if original[i:i + 4] == old_renderer]
    if old_refs != [0x5db8, 0x5fd8, 0x639c]:
        raise ValueError('Unexpected fixed-renderer caller')
    for offset in range(0, len(original) - 1, 2):
        word = struct.unpack_from('<H', original, offset)[0]
        if word >> 12 in (10, 11):
            displacement = word & 0xfff
            if displacement >= 2048:
                displacement -= 4096
            if offset + 4 + 2 * displacement == CODE_START:
                raise ValueError('Unreviewed direct branch to fixed renderer')
    patched[CODE_START:CODE_END] = code + b'\x00' * (CODE_END - CODE_START - len(code))
    changes.append((CODE_START, CODE_END))
    pool.extend(((CODE_START + len(code), CODE_END), (table_end, len(original))))
    free = [[a, z] for a, z in merged(pool) if z > a]
    placements = {}
    # Largest-first best-fit across complete banks and record padding. No source
    # slot budget, sentence trimming, file growth, BSS overlap or table resizing.
    for ordinal, blob in sorted(tasks, key=lambda item: (-len(item[1]), item[0])):
        choices = []
        for index, (a, z) in enumerate(free):
            while a in keys:
                a += 1
            if a + len(blob) <= z:
                choices.append((z - a - len(blob), a, index))
        if not choices:
            raise ValueError('Full translation allocation failed at row {} ({} bytes); add storage, do not truncate'.format(ordinal, len(blob)))
        _, a, index = min(choices)
        patched[a:a + len(blob)] = blob
        placements[ordinal] = a
        bindings[ordinal - 1]['target_file_offset'] = a
        if 'storage' not in bindings[ordinal - 1]:
            bindings[ordinal - 1]['storage'] = 'repacked_shared_text_banks'
        free[index][0] = a + len(blob)
    for a, z in pool:
        changes.append((a, z))
    ordered = sorted(mapped, key=lambda b: b['source_file_offset'])
    for i, binding in enumerate(ordered):
        struct.pack_into('<II', patched, map_start + 8 * i, BASE + binding['source_file_offset'], BASE + binding['target_file_offset'])
    for i, ordinal in enumerate(markers):
        struct.pack_into('<I', patched, marker_start + 4 * i, BASE + placements[ordinal])
    changes.append((map_start, table_end))
    pointer_count = 0
    for binding, row in zip(bindings[:560], rows[:560]):
        old_pointer = struct.pack('<I', BASE + row['file_offset'])
        refs, at = [], original.find(old_pointer)
        while at >= 0:
            refs.append(at)
            at = original.find(old_pointer, at + 1)
        if refs != row['absolute_pointer_locations'] or not all(0x12e670 <= p < 0x12f410 for p in refs):
            raise ValueError('Unexpected menu pointer alias')
        for pointer in refs:
            struct.pack_into('<I', patched, pointer, BASE + binding['target_file_offset'])
            changes.append((pointer, pointer + 4))
        pointer_count += len(refs)
        binding['pointer_locations'] = refs
    for char, codepoint in BRACKETS.items():
        offset = CONVERTER_START + 36 + 2 * (char - 32)
        struct.pack_into('<H', patched, offset, codepoint)
        changes.append((offset, offset + 2))
    assert len(patched) == len(original)
    covered = bytearray(len(original))
    for a, z in changes:
        covered[a:z] = b'\x01' * (z - a)
    assert all(x == y or covered[i] for i, (x, y) in enumerate(zip(original, patched)))
    for binding, text in zip(bindings, texts):
        a = binding['target_file_offset']
        assert patched[a:patched.index(0, a)].decode('ascii') == text
    return bytes(patched), {'version': VERSION, 'language': 'en', 'translated_game_entries': 793,
        'inventoried_game_entries': 793, 'network_entries_translated': 0,
        'source_program_sha256': digest(original), 'target_program_sha256': digest(patched),
        'program_bytes': len(patched), 'batches': [{'file': path.name, 'sha256': digest(path.read_bytes()),
            'slice': batch['slice'], 'meaning_review': batch['review']} for path, batch in loaded],
        'retargeted_menu_pointer_locations': pointer_count, 'supplemental_address_mappings': len(mapped),
        'fixed_record_name_handles': len(markers), 'resolver': {'entry': resolve, 'code_bytes': len(code),
            'table_start': map_start, 'table_end': table_end, 'hooks': hooks},
        'allocation': {'pooled_available_bytes': sum(z - a for a, z in pool),
            'pooled_target_bytes': sum(len(blob) for _, blob in tasks),
            'remaining_fragment_bytes': sum(z - a for a, z in free),
            'free_fragments': free, 'individual_slot_limits': False},
        'changed_regions': merged(changes), 'bindings': bindings,
        'limitations': ['No emulator/hardware playtest or approved screen-fit limits.',
            'Browser messages, uncounted artwork and player-created text are outside the 793-record inventory.',
            'Long tournament names use reserved copiable @E-letter display handles in native record fields.']}
