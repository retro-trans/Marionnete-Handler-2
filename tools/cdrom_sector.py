"""CD-ROM MODE1 EDC/ECC regeneration; user data starts at byte 16.

Uses the standard CD-ROM EDC polynomial and P/Q Reed-Solomon parity layout.
Parity is always regenerated for edited sectors; headers and sectors retain
their original positions. This module has no file-writing operations.
"""
import struct

EDC = []
ECC_F = []
ECC_B = [0] * 256
for index in range(256):
    value = index
    for _ in range(8):
        value = (value >> 1) ^ (0xd8018001 if value & 1 else 0)
    EDC.append(value)
    value = index << 1
    if value & 0x100:
        value ^= 0x11d
    ECC_F.append(value)
    ECC_B[index ^ value] = index


def edc(data):
    value = 0
    for byte in data:
        value = (value >> 8) ^ EDC[(value ^ byte) & 255]
    return value


def ecc(source, major_count, minor_count, major_mult, minor_inc):
    size = major_count * minor_count
    output = bytearray(major_count * 2)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            value = source[index]
            index = (index + minor_inc) % size
            a ^= value
            b ^= value
            a = ECC_F[a]
        a = ECC_B[ECC_F[a] ^ b]
        output[major] = a
        output[major + major_count] = a ^ b
    return output


def regenerate(sector):
    if len(sector) != 2352 or sector[:12] != b'\x00' + b'\xff' * 10 + b'\x00' or sector[15] != 1:
        raise ValueError('Expected a raw MODE1/2352 sector')
    output = bytearray(sector)
    struct.pack_into('<I', output, 2064, edc(output[:2064]))
    output[2068:2076] = b'\x00' * 8
    output[2076:2248] = ecc(output[12:2076], 86, 24, 2, 86)
    output[2248:2352] = ecc(output[12:2248], 52, 43, 86, 88)
    return bytes(output)
