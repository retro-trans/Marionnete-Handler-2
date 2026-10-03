"""Fit enemy help, pause captions, confirmation choices and stacked stats."""
import hashlib
import json
import struct

from build_english import prepare_native_cache
from build_vwf import BASE
from full_english import batches, merged
from inspect_disc_text import ROOT
from sh4_patch import Assembler
from shop_description_layout import hook
from validate_vwf import CPU

VERSION = '0.1.17'
POLICY = ROOT / 'work/translation/en/battle_layout_0.1.17.json'
WIDTH, HEIGHT = 300, 132


def helper(start, kind):
    a = Assembler(start)
    constants = []
    def number(value, register=0):
        marker = 0x12400000 + len(constants)
        constants.append((marker, float(value)))
        a.load(0, marker)
        a.emit(0xf008 | register << 8)
    def store(offset, value):
        number(value)
        a.emit(0x6013, 0x7000 | offset, 0xf00a)
    a.emit(0x2f16, 0x2f26)
    a.load(0, 0x8c1a428c if kind == 'enemy' else 0x8c1a4320)
    a.emit(0x6402, 0xe02c, 0x0407, 0x041a)
    a.load(3, 0x8c1a4328 if kind == 'enemy' else 0x8c1a4408)
    a.emit(0x6133, 0x314c)  # r1 = window record; r4 = index * 44
    if kind == 'enemy':
        for offset, low, high in ((4, 8, 632 - WIDTH), (8, 52, 472 - HEIGHT)):
            a.emit(0x6013, 0x7000 | offset, 0xf108)
            number(low)
            a.emit(0xf105)
            a.branch(0x8900, 'low_' + str(offset))
            a.emit(0xf10c)
            a.label('low_' + str(offset))
            number(high)
            a.emit(0xf105)
            a.branch(0x8b00, 'high_' + str(offset))
            a.emit(0xf10c)
            a.label('high_' + str(offset))
            a.emit(0x6013, 0x7000 | offset, 0xf01a)
        for offset, value in ((16, WIDTH), (20, HEIGHT), (32, WIDTH), (36, HEIGHT)):
            store(offset, value)
        continuation = 0x19bd4
    else:
        # Detailed stats need fourteen more pixels. Move Equipment below them
        # only when it is open and would overlap; retain a larger existing gap.
        a.load(0, 0x8c2c8bc0 + 60)
        a.emit(0x6000, 0x2008)
        a.branch(0x8900, 'done')
        a.load(0, 0x8c1a4314)
        a.emit(0x6202, 0x4211)  # equipment index; cmp/pz
        a.branch(0x8b00, 'done')
        a.emit(0xe02c, 0x0207, 0x021a, 0x323c)
        a.emit(0x6013, 0x7008, 0xf108)
        number(182)
        a.emit(0xf105)
        a.branch(0x8b00, 'stats_y_ok')
        a.emit(0xf10c, 0x6013, 0x7008, 0xf01a)
        a.emit(0x6013, 0x701c, 0xf01a)
        a.label('stats_y_ok')
        a.emit(0xfe1c)
        number(19)
        a.emit(0xfe00)  # rebase the already computed native label/value origin
        number(206)
        a.emit(0xf100)  # desired equipment top = stats y + 202 + 4
        a.emit(0x6023, 0x7008, 0xf208, 0xf215)
        a.branch(0x8900, 'done')
        a.emit(0xf01a, 0x6023, 0x701c, 0xf01a)
        a.label('done')
        continuation = 0x43660
    a.emit(0x62f6, 0x61f6)
    a.load(0, BASE + continuation)
    a.emit(0x402b, 0x0009)
    blob = a.finish()
    for marker, value in constants:
        blob = blob.replace(struct.pack('<I', marker), struct.pack('<I', start + len(blob)))
        blob += struct.pack('<f', value)
    return blob


def plan(original, program, report):
    result = bytearray(program)
    _, texts, _ = batches()
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    assert policy['version'] == VERSION
    entries = policy['translations']
    assert sorted(e['row'] for e in entries) == [98] + list(range(229, 235)) + list(range(413, 417))
    changes = list(report['changed_regions'])
    metrics = {r['character']: r['advance'] for r in report['font_asset']['latin_metrics']}
    metrics[' '] = report['space_advance_px']
    for entry in entries:
        row, text = entry['row'], entry['target']
        source = texts[row - 1]
        assert source == entry['full_translation'] and len(text) <= len(source)
        if row >= 413:
            assert source.split() == text.split()
            assert len(source) == len(text) and text.count('\n') <= 4
        binding = report['bindings'][row - 1]
        at = binding['target_file_offset']
        assert result[at:at + len(source) + 1] == source.encode() + b'\0'
        result[at:at + len(source) + 1] = text.encode().ljust(len(source) + 1, b'\0')
        binding.update(target_bytes=len(text), target_sha256=hashlib.sha256(text.encode()).hexdigest(),
                       line_count=text.count('\n') + 1, review_note=entry['note'])
        report['layout_overrides'][str(row)] = text
        entry['line_advances'] = [sum(metrics[c] for c in line) for line in text.split('\n')]
        assert max(entry['line_advances']) <= (122 if row in range(229, 235) else 268)
        changes.append((at, at + len(source) + 1))
    # The prefix is an unlisted native positioning string, shared by dialogs.
    prefix = 0x12de38
    old = b'\n' + b'\x81\x40' * 17 + b'\0'
    assert original[prefix:prefix + len(old)] == old
    assert result[prefix:prefix + len(old)] == old
    result[prefix:prefix + len(old)] = b'\n@x150\0'.ljust(len(old), b'\0')
    changes.append((prefix, prefix + len(old)))
    for at, old_value, value in ((0x4373c, 188, 202), (0x43c64, 78, 92)):
        assert struct.unpack_from('<f', original, at)[0] == old_value
        struct.pack_into('<f', result, at, value)
        changes.append((at, at + 4))
    helpers = {}
    for kind, site in (('enemy', 0x19bc8), ('stats', 0x43654)):
        for fragment in report['allocation']['free_fragments']:
            start, end = fragment
            start = (start + 3) & ~3
            blob = helper(BASE + start, kind)
            if start + len(blob) <= end:
                break
        else:
            raise ValueError('No free owned fragment for ' + kind)
        assert program[site:site + 12] == original[site:site + 12]
        result[start:start + len(blob)] = blob
        fragment[0] = start + len(blob)
        hook(result, site, BASE + start)
        changes += [(start, start + len(blob)), (site, site + 12)]
        helpers[kind] = {'file_offset': start, 'size': len(blob), 'hook': site}
    report['allocation']['remaining_fragment_bytes'] = sum(z-a for a,z in report['allocation']['free_fragments'])
    report.update(version=VERSION, battle_layout={'entries': entries, 'enemy_window': [WIDTH, HEIGHT],
                  'helpers': helpers, 'confirmation_prefix': {'offset': prefix, 'target': '\n@x150'},
                  'stats_height': 202, 'equipment_height': 92}, changed_regions=merged(changes),
                  target_program_sha256=hashlib.sha256(result).hexdigest())
    return bytes(result)


def validate(program, report, metrics):
    template, _, codes, _ = prepare_native_cache(program)
    for i, code in enumerate(codes):
        bearing, advance = metrics[code]
        template.write(0x8c34dbb4+i, bearing, 1)
        template.write(0x8c34de28+i, advance, 1)
    def setup():
        c = CPU(program)
        c.mem[0x34d6d0:0x34e0c0] = template.mem[0x34d6d0:0x34e0c0]
        c.write(0x8c13d75c, 1)
        c.write_float(0x8c13d758, 100)
        return c
    def capture(c):
        vertices = []
        def submit():
            vertices.extend((c.read_float(c.r[4]+i*24),c.read_float(c.r[4]+i*24+4)) for i in range(4))
            c.submit()
        c.stubs[0x8c1731a4] = submit
        return vertices
    def bounds(v):
        return [min(x for x,y in v),min(y for x,y in v),max(x for x,y in v),max(y for x,y in v)]
    enemy_cases = []
    for index in range(4):
        for px, py in ((64,60),(-230,-50),(500,420)):
            c=setup();v=capture(c)
            c.write(0x8c1a428c, 2);c.write(0x8c1a430c, 1)
            parent=0x8c1a4408+44;window=0x8c1a4328+88
            c.write_float(parent+4,px);c.write_float(parent+8,py)
            c.write_float(window+12,100);c.r[4]=index
            c.run(BASE+0x19b78,limit=3000000)
            x=min(max(px+200,8),332);y=min(max(py+67,52),340)
            assert c.read_float(window+4)==x and c.read_float(window+8)==y
            for off,val in ((16,WIDTH),(20,HEIGHT),(32,WIDTH),(36,HEIGHT)):
                assert c.read_float(window+off)==val
            box=bounds(v);assert x<=box[0]<=box[2]<=x+WIDTH and y<=box[1]<=box[3]<=y+HEIGHT,(index,box)
            assert c.r[15]==0x8cf00000
            rectangles=[]
            c.stubs[BASE+0x91dc]=lambda:rectangles.append([c.read_float(0x8c1a34e4+i*4) for i in range(4)])
            c.stubs[BASE+0x93d4]=lambda:None
            c.r[4]=2;c.run(BASE+0x10a5c)
            assert rectangles[0]==[x,y+2,x+WIDTH,y+2+HEIGHT]
            enemy_cases.append({'selection':index,'panel':[x,y,x+WIDTH,y+HEIGHT],'glyphs':box})
    menus=[]
    for row in range(229,235):
        c=setup();v=capture(c)
        c.write_float(0x8c34e0c0,16);c.write_float(0x8c34e0c4,16)
        c.r[4]=struct.unpack_from('<I',program,report['bindings'][row-1]['pointer_locations'][0])[0]
        c.run(BASE+0x6090,limit=3000000)
        box=bounds(v);assert box[2]<=142,(row,box)
        menus.append({'row':row,'glyphs':box})
    dialogs=[]
    for selection in (0,1,3):
        c=setup();v=capture(c)
        c.write(0x8c1a427c,2);c.write(0x8c1a4644,5);c.write(0x8c1a4634,selection)
        window=0x8c1a4328+88
        c.write_float(window+4,168);c.write_float(window+8,188);c.write_float(window+12,100)
        c.write(0x8c1b21e4,255);c.write(0x8c2c8b80+20,0xffffff)
        c.run(BASE+0x11464,stop=BASE+0x11552,limit=3000000)
        box=bounds(v);assert 168<=box[0]<=box[2]<=468 and 188<=box[1]<=box[3]<=270,box
        assert c.r[15]==0x8cf00000
        dialogs.append({'selection':selection,'glyphs':box})
    stats=[]
    # Execute the detailed stats geometry prefix and the real Equipment caller.
    # Small-font quads are 11 pixels; capture their actual native X/Y positions.
    for sy,ey in ((174,366),(174,386),(240,366)):
        c=setup();c.write(0x8c1a4320,1);c.write(0x8c1a4314,2)
        c.write(0x8c2c8bc0+60,1,1)
        c.f[13:16]=[100,sy+19,0]
        sw=0x8c1a4408+44;ew=0x8c1a4408+88
        c.write_float(sw+8,sy);c.write_float(ew+8,ey)
        c.run(BASE+0x43654,stop=BASE+0x43686,limit=3000000)
        top=min(sy,182);equipment_top=max(ey,top+206)
        assert c.read_float(sw+8)==top and c.read_float(sw+20)==202
        assert c.f[14]==top+19
        assert c.read_float(ew+8)==equipment_top
        small=[]
        c.stubs[BASE+0x7a24]=lambda:small.append([c.f[4],c.f[5],c.f[4]+11,c.f[5]+11])
        c.run(BASE+0x43686,stop=BASE+0x436a4,limit=3000000)
        assert max(q[3] for q in small)<equipment_top,(sy,ey,small[-1])
        stats_bottom=max(q[3] for q in small)
        c.write(0x8c1a4628,1)
        c.write(0x8c2c8bc0+32,1)
        c.write(0x8c2c8bc0+60,1,1)
        small.clear()
        c.run(BASE+0x439a0,limit=3000000)
        assert c.read_float(ew+20)==92 and c.read_float(ew+36)==92
        assert max(q[3] for q in small)<=480
        assert c.r[15]==0x8cf00000
        stats.append({'stats_top':top,
                      'equipment_top':equipment_top,'stats_text_bottom':stats_bottom,
                      'equipment_text_bottom':max(q[3] for q in small)})
    print('Battle: 4 enemy descriptions, 6 pause captions, Yes/No choices and detailed stats fit.',flush=True)
    return {'enemy_cases':enemy_cases,'pause_captions':menus,'confirmation_choices':dialogs,
            'stats_stacking':stats,'actual_Flycast_playtest':False}
