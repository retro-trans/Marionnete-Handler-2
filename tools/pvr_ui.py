"""Lossless pixel addressing for this game's square, twiddled 16-bit UI PVRs.

Only uncompressed ARGB1555/RGB565/ARGB4444 is supported. Headers, storage
length and pixels outside explicitly edited rectangles remain unchanged.
"""
import struct

from PIL import Image


def layout(data):
    offset = 0
    if data[:4] == b'GBIX':
        offset = 8 + struct.unpack_from('<I', data, 4)[0]
    assert data[offset:offset + 4] == b'PVRT'
    length = struct.unpack_from('<I', data, offset + 4)[0]
    pixel, storage, reserved, width, height = struct.unpack_from('<BBHHH', data, offset + 8)
    assert storage == 1 and pixel in (0, 1, 2), (pixel, storage)
    assert width == height and width > 0 and width & (width - 1) == 0
    assert length == 8 + width * height * 2 and len(data) == offset + 8 + length
    return offset + 16, pixel, width, height


def address(x, y):
    value = 0
    bit = 0
    while x or y:
        value |= (y & 1) << (2 * bit)
        value |= (x & 1) << (2 * bit + 1)
        x >>= 1
        y >>= 1
        bit += 1
    return value * 2


def unpack(value, pixel):
    if pixel == 2:
        return ((value >> 8 & 15) * 17, (value >> 4 & 15) * 17,
                (value & 15) * 17, (value >> 12) * 17)
    if pixel == 1:
        return (round((value >> 11) * 255 / 31),
                round((value >> 5 & 63) * 255 / 63), round((value & 31) * 255 / 31), 255)
    return (round((value >> 10 & 31) * 255 / 31),
            round((value >> 5 & 31) * 255 / 31), round((value & 31) * 255 / 31),
            255 if value & 0x8000 else 0)


def pack(rgba, pixel):
    r, g, b, a = rgba
    if pixel == 2:
        return round(a / 17) << 12 | round(r / 17) << 8 | round(g / 17) << 4 | round(b / 17)
    if pixel == 1:
        return round(r * 31 / 255) << 11 | round(g * 63 / 255) << 5 | round(b * 31 / 255)
    return (0x8000 if a >= 128 else 0) | round(r * 31 / 255) << 10 | round(g * 31 / 255) << 5 | round(b * 31 / 255)


def decode(data):
    base, pixel, width, height = layout(data)
    image = Image.new('RGBA', (width, height))
    image.putdata([unpack(struct.unpack_from('<H', data, base + address(x, y))[0], pixel)
                   for y in range(height) for x in range(width)])
    return image


def encode_rectangles(data, image, rectangles):
    base, pixel, width, height = layout(data)
    assert image.mode == 'RGBA' and image.size == (width, height)
    result = bytearray(data)
    for left, top, right, bottom in rectangles:
        assert 0 <= left < right <= width and 0 <= top < bottom <= height
        for y in range(top, bottom):
            for x in range(left, right):
                struct.pack_into('<H', result, base + address(x, y), pack(image.getpixel((x, y)), pixel))
    return bytes(result)
