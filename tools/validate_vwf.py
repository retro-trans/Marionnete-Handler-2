"""Execute VWF SH-4 routines in a limited instruction harness, not a Dreamcast emulator.

The game converter, width lookup, proportional renderer and numeric formatters
execute their actual machine code. Platform texture wait/submit and integer
division are replaced by explicit stubs. Synthetic cache metrics exercise
variable advances without depending on a particular Dreamcast BIOS.
Default prints results only; --report saves source-free validation evidence.
"""
import argparse
import hashlib
import json
import shlex
import struct

from build_vwf import BASE, CONVERTER_START, WIDTH_TABLE, plan, original_conversion, patched_conversion
from inspect_disc_text import Disc, ROOT
from cdrom_sector import regenerate


def signed(value, bits=32):
    return (value & ((1 << bits) - 1)) - ((1 << bits) if value & (1 << (bits - 1)) else 0)


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


class CPU:
    """Restricted SH-4, single-precision, little-endian instruction harness."""
    def __init__(self, program):
        self.mem = bytearray(16 * 1024 * 1024)
        self.mem[0x10000:0x10000 + len(program)] = program
        self.r = [0] * 16
        self.f = [0.0] * 16
        self.r[15] = 0x8cf00000
        self.pr = 0x8cfffffc
        self.fpul = 0
        self.macl = 0
        self.t = False
        self.pc = 0
        self.pending = None
        self.vertices = []
        self.stubs = {0x8c010234: self.modulo, 0x8c0100fc: self.divide,
                      0x8c16c214: self.wait, 0x8c1731a4: self.submit,
                      0x8c017a24: self.small_draw}

    def read(self, address, size=4):
        offset = address - 0x8c000000
        if not 0 <= offset <= len(self.mem) - size:
            raise ValueError('Read outside RAM: {:08x}'.format(address))
        return int.from_bytes(self.mem[offset:offset + size], 'little')

    def write(self, address, value, size=4):
        offset = address - 0x8c000000
        if not 0 <= offset <= len(self.mem) - size:
            raise ValueError('Write outside RAM: {:08x}'.format(address))
        self.mem[offset:offset + size] = (value & ((1 << (size * 8)) - 1)).to_bytes(size, 'little')

    def read_float(self, address):
        return struct.unpack('<f', self.read(address).to_bytes(4, 'little'))[0]

    def write_float(self, address, value):
        self.write(address, int.from_bytes(struct.pack('<f', value), 'little'))

    def modulo(self):
        self.r[0] = self.r[4] % self.r[5]

    def divide(self):
        self.r[0] = self.r[4] // self.r[5]

    def wait(self):
        self.r[0] = 0

    def submit(self):
        assert self.r[5] == 4 and self.r[6] == 0x11000002
        self.vertices.append([self.read_float(self.r[4] + i * 24) for i in range(4)])

    def small_draw(self):
        self.vertices.append([self.f[4], self.f[4] + 11, self.f[4], self.f[4] + 11])

    def run(self, address, stop=None, limit=100000):
        self.pc = address
        stop = self.pr if stop is None else stop
        self.pending = None
        for _ in range(limit):
            if self.pc == stop:
                return
            if self.pc in self.stubs:
                self.stubs[self.pc]()
                self.pc = self.pr
                continue
            self.step()
        raise AssertionError('Instruction limit exceeded at {:08x}'.format(self.pc))

    def step(self):
        pc = self.pc
        op = self.read(pc, 2)
        n, m, low, high = (op >> 8) & 15, (op >> 4) & 15, op & 15, op >> 12
        old_pending = self.pending
        self.pending = None
        next_pc = pc + 2
        r = self.r
        if op == 0x0009:
            pass
        elif op == 0x000b:
            self.pending = self.pr
        elif high == 0xe:
            r[n] = signed(op & 255, 8)
        elif high == 0x7:
            r[n] += signed(op & 255, 8)
        elif high == 0xd:
            r[n] = self.read(((pc + 4) & ~3) + (op & 255) * 4)
        elif high == 0x9:
            r[n] = signed(self.read(pc + 4 + (op & 255) * 2,2),16)
        elif op & 0xff00 == 0xc700:
            r[0] = ((pc + 4) & ~3) + (op & 255) * 4
        elif op & 0xff00 == 0xc900:
            r[0] &= op & 255
        elif high in (0xa, 0xb):
            if high == 0xb:
                self.pr = pc + 4
            self.pending = pc + 4 + signed(op & 0xfff, 12) * 2
        elif op & 0xff00 in (0x8900, 0x8b00, 0x8d00, 0x8f00):
            branch = self.t if (op & 0xff00) in (0x8900, 0x8d00) else not self.t
            target = pc + 4 + signed(op & 255, 8) * 2
            if op & 0xff00 in (0x8d00, 0x8f00):
                self.pending = target if branch else pc + 4
            elif branch:
                next_pc = target
        elif op & 0xff00 == 0x8800:
            self.t = r[0] == (signed(op & 255, 8) & 0xffffffff)
        elif op & 0xf0ff in (0x400b, 0x402b):
            self.pending = r[n]
            if op & 0xff == 0x0b:
                self.pr = pc + 4
        elif op & 0xf0ff == 0x4022:
            r[n] -= 4
            self.write(r[n], self.pr)
        elif op & 0xf0ff == 0x4026:
            self.pr = self.read(r[n])
            r[n] += 4
        elif op & 0xf0ff == 0x405a:
            self.fpul = signed(r[n])
        elif op & 0xf0ff == 0x005a:
            r[n] = self.fpul
        elif op & 0xf0ff == 0x001a:
            r[n] = self.macl
        elif op & 0xf0ff in (0x4011, 0x4015):
            self.t = signed(r[n]) >= 0 if op & 255 == 0x11 else signed(r[n]) > 0
        elif op & 0xf0ff == 0x4000:
            self.t = bool(r[n] & 0x80000000)
            r[n] <<= 1
        elif op & 0xf0ff == 0x4001:
            self.t = bool(r[n] & 1)
            r[n] >>= 1
        elif op & 0xf0ff == 0x4010:
            r[n] -= 1
            self.t = (r[n] & 0xffffffff) == 0
        elif op & 0xf0ff in (0x4008, 0x4018, 0x4028):
            r[n] <<= {8:2, 0x18:8, 0x28:16}[op & 255]
        elif op & 0xf0ff in (0x4009, 0x4019, 0x4029):
            r[n] >>= {9:2, 0x19:8, 0x29:16}[op & 255]
        elif high == 4 and low in (0xc,0xd):
            shift=signed(r[m])
            if shift>=0:
                r[n] <<= shift&31
            else:
                amount=(-shift)&31
                value=signed(r[n]) if low==0xc else r[n]
                r[n]=value>>(amount or 32)
        elif high == 0x6:
            if low == 3:
                r[n] = r[m]
            elif low in (0, 1, 2, 4, 5, 6):
                size = (1, 2, 4)[low % 4]
                value = self.read(r[m], size)
                r[n] = signed(value, size * 8) if size < 4 else value
                if low >= 4 and n != m:
                    r[m] += size
            elif low == 0xb:
                r[n] = -r[m]
            elif low == 0xc:
                r[n] = r[m] & 255
            elif low == 0xd:
                r[n] = r[m] & 65535
            elif low == 0xe:
                r[n] = signed(r[m], 8)
            else:
                raise ValueError('Unsupported 6xxx {:04x}'.format(op))
        elif high == 0x2:
            if low in (0, 1, 2, 4, 5, 6):
                size = (1, 2, 4)[low % 4]
                if low >= 4:
                    r[n] -= size
                self.write(r[n], r[m], size)
            elif low == 8:
                self.t = (r[n] & r[m]) == 0
            elif low == 0xb:
                r[n] |= r[m]
            elif low == 9:
                r[n] &= r[m]
            else:
                raise ValueError('Unsupported 2xxx {:04x}'.format(op))
        elif high == 0x3:
            if low == 0:
                self.t = r[n] == r[m]
            elif low == 2:
                self.t = r[n] >= r[m]
            elif low == 3:
                self.t = signed(r[n]) >= signed(r[m])
            elif low == 6:
                self.t = r[n] > r[m]
            elif low == 7:
                self.t = signed(r[n]) > signed(r[m])
            elif low == 0xc:
                r[n] += r[m]
            elif low == 8:
                r[n] -= r[m]
            else:
                raise ValueError('Unsupported 3xxx {:04x}'.format(op))
        elif high == 0 and low in (0xc, 0xd, 0xe):
            size = (1, 2, 4)[low - 0xc]
            value = self.read(r[0] + r[m], size)
            r[n] = signed(value, size * 8) if size < 4 else value
        elif high == 0 and low in (4, 5, 6):
            self.write(r[0] + r[n], r[m], (1, 2, 4)[low - 4])
        elif high == 0 and low == 7:
            self.macl = (r[n] * r[m]) & 0xffffffff
        elif high == 1:
            self.write(r[n] + low * 4, r[m])
        elif high == 5:
            r[n] = self.read(r[m] + low * 4)
        elif high == 0xf:
            if low in (0, 1, 2, 3):
                a, b = self.f[n], self.f[m]
                self.f[n] = f32((a + b, a - b, a * b, a / b if b else 0)[low])
            elif low in (4, 5):
                self.t = self.f[n] == self.f[m] if low == 4 else self.f[n] > self.f[m]
            elif low in (8, 9):
                self.f[n] = self.read_float(r[m])
                if low == 9:
                    r[m] += 4
            elif low in (0xa, 0xb):
                if low == 0xb:
                    r[n] -= 4
                self.write_float(r[n], self.f[m])
            elif low == 0xc:
                self.f[n] = self.f[m]
            elif low == 0xd and m == 2:
                self.f[n] = f32(self.fpul)
            elif low == 0xd and m == 3:
                self.fpul = int(self.f[n])
            elif low == 0xd and m == 4:
                self.f[n] = f32(-self.f[n])
            elif low == 0xd and m == 8:
                self.f[n] = 0.0
            elif low == 0xd and m == 9:
                self.f[n] = 1.0
            else:
                raise ValueError('Unsupported float {:04x}'.format(op))
        else:
            raise ValueError('Unsupported opcode {:04x} at {:08x}'.format(op, pc))
        self.r = [value & 0xffffffff for value in r]
        self.pc = old_pending if old_pending is not None else next_pc


def seed_cache(cpu):
    widths = {}
    # Deliberately unequal synthetic BIOS widths, including narrow punctuation.
    for i, char in enumerate(range(32, 127)):
        code = patched_conversion(char)
        width = 6 if char in (32, 44, 46) else 8 if char == 49 else 11 + char % 5
        widths[char] = width
        cpu.write(0x8c34d6d0 + 2 * i, code, 2)
        cpu.write(0x8c34de28 + i, width, 1)
        cpu.write(0x8c34dbb4 + i, i % 3, 1)
    return widths


def validate():
    disc = Disc()
    entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
    original = disc.read(entry['lba'], entry['size'])
    patched, report = plan(original)
    checked = []
    for data, convert in ((original, original_conversion), (patched, patched_conversion)):
        cpu = CPU(data)
        for value in range(256):
            cpu.r[4] = value
            cpu.run(BASE + CONVERTER_START)
            assert cpu.r[0] == convert(value), (value, cpu.r[0], convert(value))
            assert cpu.r[4] == value and cpu.r[15] == 0x8cf00000
        checked.append('256 {} converter byte inputs'.format('original' if data is original else 'patched'))
    cpu = CPU(patched)
    widths = seed_cache(cpu)
    for char in range(32, 127):
        cpu.r[4], cpu.r[5] = 1, patched_conversion(char)
        cpu.run(BASE + 0x839c)
        assert cpu.r[0] == widths[char]
        cpu.r[4], cpu.f[4], cpu.f[5], cpu.f[6] = patched_conversion(char), 100.0, 40.0, 1.0
        cpu.run(BASE + 0x7f64)
        assert cpu.f[0] == widths[char]
        assert cpu.r[15] == 0x8cf00000
    cpu.r[4], cpu.r[5] = 1, 0xffff
    cpu.run(BASE + 0x839c)
    assert cpu.r[0] == 20
    cpu.r[4] = 0xffff
    cpu.run(BASE + 0x7f64)
    assert cpu.f[0] == 20
    checked.append('95 cached glyph widths match native proportional renderer; missing glyph returns 20')
    string_cases = 0
    for mode in (1, 4):
        for raw, expected in ((b'Wiil', 100 + sum(widths[c] for c in b'Wiil')),
                              (b'@x020Wiil', 50 + 20 + sum(widths[c] for c in b'Wiil')),
                              (b'@r200Wiil', 250),
                              (b'Wi\nl', 50 + widths[ord('l')]),
                              (b'W\x82\xa0i', 100 + widths[ord('W')] + 20 + widths[ord('i')]),
                              (b'{|}~', 100 + sum(widths[c] for c in b'{|}~'))):
            cpu = CPU(patched)
            seed_cache(cpu)
            cpu.write(0x8c13d75c, mode)
            cpu.write_float(0x8c34e0c0, 100.0)
            cpu.write_float(0x8c34e0c4, 50.0)
            cpu.write_float(0x8c34e0c8, 40.0)
            cpu.write_float(0x8c13d758, 1.0)
            for i, byte in enumerate(raw):
                cpu.write(0x8ce00000 + i, byte, 1)
            cpu.r[4] = 0x8ce00000
            cpu.run(BASE + 0x6090)
            assert cpu.f[0] == expected, (raw, mode, cpu.f[0], expected)
            assert cpu.read_float(0x8c34e0c8) == (62.0 if b'\n' in raw else 40.0)
            assert cpu.r[15] == 0x8cf00000
            string_cases += 1
    checked.append('{} actual string dispatcher cases: fonts 1/4, narrow/wide Latin, mixed CP932, new punctuation, newline, @x and @r positioning'.format(string_cases))
    numeric_cases = 0
    for mode in (0, 1, 4):
        for decimal in (False, True):
            values = (0, 1, 1234, -1234, 1234567) if not decimal else (0.0, 1.25, -1234.5, 999.999)
            for value in values:
                for alignment in (-1.0, 0.0, 90.0):
                    cpu = CPU(patched)
                    widths = seed_cache(cpu)
                    cpu.write(0x8c13d75c, mode)
                    cpu.write_float(0x8c34e0c0, 100.0)
                    cpu.write_float(0x8c34e0c8, 40.0)
                    cpu.write_float(0x8c13d758, 1.0)
                    cpu.f[4] = alignment
                    cpu.f[5] = f32(value)
                    cpu.r[4] = 2 if decimal else value & 0xffffffff
                    cpu.r[8:15] = [0xabcdef00 + i for i in range(7)]
                    saved = cpu.r[8:15].copy()
                    cpu.run(BASE + (0x5dbc if decimal else 0x5c1c))
                    assert cpu.r[8:15] == saved and cpu.r[15] == 0x8cf00000
                    count = len(cpu.vertices)
                    chars = [cpu.read(0x8c34e114 + i, 1) for i in range(count)][::-1]
                    # Independently derive expected glyph positions from formatted buffer.
                    advances = [patched[WIDTH_TABLE + c - 32] + 2 if mode == 0 else widths[c] for c in chars]
                    total = sum(advances)
                    expected_start = 100.0 if alignment < 0 else 100.0 + alignment - total
                    expected_end = expected_start + total
                    assert abs(cpu.f[0] - expected_end) < 0.0001, (mode, value, alignment, cpu.f[0], expected_end)
                    pen = expected_start
                    for char, advance, vertex in zip(chars, advances, cpu.vertices):
                        bearing = 0 if mode == 0 else (char - 32) % 3
                        assert abs(vertex[0] - (pen - bearing)) < 0.0001
                        pen += advance
                    numeric_cases += 1
    checked.append('{} numeric formatter/renderer cases: fonts 0/1/4, negatives, commas, decimals, rounding, alignment and register/stack preservation'.format(numeric_cases))
    # Exact unchanged ranges guard the parser, controls, other font modes and data layout.
    intervals = [(r['file_offset'], r['file_offset'] + r['bytes']) for r in report['changes']]
    cursor = 0
    for start, end in sorted(intervals):
        assert original[cursor:start] == patched[cursor:start]
        cursor = end
    assert original[cursor:] == patched[cursor:] and len(original) == len(patched)
    assert original[0x6090:0x639c] == patched[0x6090:0x639c]
    checked.append('Only eight intended code regions change; string/control parser and executable size retained')
    # Verify all original sectors that the build will edit, independently before output.
    track_start, _, track = next(t for t in disc.tracks if t[0] <= entry['lba'] < t[1])
    sectors = []
    with track.open('rb') as stream:
        for index in range((len(patched) + 2047) // 2048):
            offset = index * 2048
            if original[offset:offset + 2048] == patched[offset:offset + 2048]:
                continue
            stream.seek((entry['lba'] - track_start + index) * 2352)
            sector = stream.read(2352)
            assert regenerate(sector) == sector
            sectors.append(entry['lba'] + index)
    checked.append('Original EDC/ECC matches regeneration for all {} edited sectors'.format(len(sectors)))
    return {'version': report['version'], 'passed': True, 'checks': checked,
            'source_program_sha256': hashlib.sha256(original).hexdigest(),
            'target_program_sha256': hashlib.sha256(patched).hexdigest(),
            'edited_sector_lbas': sectors,
            'limitations': 'Limited SH-4 harness with synthetic BIOS cache; no Dreamcast emulator boot or visual playtest performed. Platform texture submission, wait and integer division stubbed.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--built', action='store_true', help='Also inspect the generated Track 17 and GDI')
    args = parser.parse_args()
    result = validate()
    if args.built:
        folder = ROOT / 'work' / 'output' / ('vwf-' + result['version'])
        target_track = next(folder.glob('*.bin'))
        disc = Disc()
        entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
        original = disc.read(entry['lba'], entry['size'])
        target, _ = plan(original)
        start, _, source_track = next(t for t in disc.tracks if t[0] <= entry['lba'] < t[1])
        source_bytes, target_bytes = source_track.read_bytes(), target_track.read_bytes()
        assert len(source_bytes) == len(target_bytes)
        changed = []
        for index in range(len(source_bytes) // 2352):
            before = source_bytes[index * 2352:(index + 1) * 2352]
            after = target_bytes[index * 2352:(index + 1) * 2352]
            if before != after:
                assert before[:16] == after[:16] and regenerate(after) == after
                changed.append(start + index)
        assert changed == result['edited_sector_lbas']
        exe_start = (entry['lba'] - start) * 2352
        extracted = b''.join(target_bytes[pos + 16:pos + 2064] for pos in
                             range(exe_start, exe_start + ((entry['size'] + 2047) // 2048) * 2352, 2352))[:entry['size']]
        assert extracted == target
        gdi = next(folder.glob('*.gdi')).read_text(encoding='utf-8').splitlines()
        assert int(gdi[0]) == 17 and len(gdi) == 18
        for number, line in enumerate(gdi[1:], 1):
            fields = shlex.split(line)
            path = (folder / fields[4]).resolve()
            expected = target_track if number == 17 else next(ROOT.glob('*Track {:02d}*.bin'.format(number)))
            assert path == expected.resolve() and path.is_file()
            assert int(fields[0]) == number and int(fields[3]) == 2352
            assert int(fields[2]) == (4 if number in (1, 3, 17) else 0)
            skip = int(fields[5])
            assert skip == (0 if number in (1, 3) else 225 if number == 17 else 150) * 2352
            if number >= 3:
                track_start = next(t[0] for t in disc.tracks if t[2] == next(ROOT.glob('*Track {:02d}*.bin'.format(number))))
                assert int(fields[1]) == track_start + skip // 2352
        result['built_track_sha256'] = hashlib.sha256(target_bytes).hexdigest()
        result['source_track_sha256'] = hashlib.sha256(source_bytes).hexdigest()
        result['checks'].append('Built track: exact executable read-back, only four sectors differ, valid EDC/ECC, and all 17 GDI track references/offsets verified')
    print(json.dumps(result, indent=2))
    if args.report:
        (ROOT / 'work' / 'ui' / 'vwf_validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
