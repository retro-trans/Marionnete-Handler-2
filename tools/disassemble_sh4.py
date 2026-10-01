"""Disassemble read-only game code with Capstone 5 (use 64-bit Python)."""
import argparse
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).parent / 'vendor'))
import capstone
from inspect_disc_text import Disc


def disassemble(data, start, end, base=0x8c010000):
    md = capstone.Cs(capstone.CS_ARCH_SH,
                     capstone.CS_MODE_SH4 | capstone.CS_MODE_SHFPU | capstone.CS_MODE_LITTLE_ENDIAN)
    for offset in range(start, end, 2):
        raw = data[offset:offset + 2]
        instruction = next(md.disasm(raw, base + offset), None)
        if instruction is None:
            print('{:06x}: {} .word'.format(offset, raw.hex()))
            continue
        word = struct.unpack('<H', raw)[0]
        comment = ''
        if word >> 12 == 0xd:
            loc = ((offset + 4) & ~3) + (word & 255) * 4
            value = struct.unpack_from('<I', data, loc)[0]
            comment = ' ; [{:06x}] = {:08x}'.format(loc, value)
        elif word >> 12 == 0x9:
            loc = offset + 4 + (word & 255) * 2
            value = struct.unpack_from('<H', data, loc)[0]
            comment = ' ; [{:06x}] = {:04x}'.format(loc, value)
        print('{:06x}: {} {:8} {}{}'.format(offset, raw.hex(), instruction.mnemonic, instruction.op_str, comment))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('start', type=lambda s: int(s, 0))
    parser.add_argument('end', type=lambda s: int(s, 0))
    args = parser.parse_args()
    disc = Disc()
    entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
    disassemble(disc.read(entry['lba'], entry['size']), args.start, args.end)


if __name__ == '__main__':
    main()
