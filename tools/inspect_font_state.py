"""Read a Flycast save state and report font allocation evidence only."""
import argparse
import json
import struct
import zlib
from pathlib import Path

from inspect_disc_text import Disc


def read_ram(path):
    data=Path(path).read_bytes()
    offset=24+struct.unpack_from('<I',data,20)[0] if data[:8]==b'FLYSAVE1' else 0
    if data[offset:offset+8]!=b'#RZIPv\x01#':
        raise ValueError('Unsupported Flycast save-state compression')
    total=struct.unpack_from('<Q',data,offset+12)[0]
    offset+=20
    chunks=[];size=0
    while size<total:
        length=struct.unpack_from('<I',data,offset)[0];offset+=4
        chunk=zlib.decompress(data[offset:offset+length]);offset+=length
        chunks.append(chunk);size+=len(chunk)
    if size!=total:
        raise ValueError('Save-state length mismatch')
    blob=b''.join(chunks)
    disc=Disc();entry=next(e for e in disc.files if e['path']=='/1ST_READ.BIN')
    signature=disc.read(entry['lba'],48)
    if blob.count(signature)!=1:
        raise ValueError('Cannot uniquely locate game RAM')
    start=blob.index(signature)-0x10000
    ram=blob[start:start+0x1000000]
    if len(ram)!=0x1000000:
        raise ValueError('Captured RAM is truncated')
    return ram


def font_state(path):
    ram=read_ram(path)
    def u(address):
        return struct.unpack_from('<I',ram,address-0x8c000000)[0]
    pointer=u(0x8c2cd63c)
    descriptor=[u(0x8c34d6a4+i*4) for i in range(6)]
    width,height=descriptor[4:6]
    if not (0x8c000000<=pointer and pointer+width*height*2<=0x8d000000):
        raise ValueError('Font atlas is outside captured RAM')
    atlas=ram[pointer-0x8c000000:pointer-0x8c000000+width*height*2]
    table=u(u(0x8c1a000c));texture=u(table+2*12+8)
    report={'save_state':Path(path).name,'atlas_pointer':hex(pointer),
            'dimensions':[width,height],'cache_count':u(0x8c34e0ac),
            'atlas_nonzero_pixels':sum(v!=0 for (v,) in struct.iter_unpack('<H',atlas)),
            'texture_object':hex(texture),'hardware_size_bits':u(texture+8)&63,
            'hardware_texture_word':hex(u(texture+12)),
            'texture_bytes':u(texture+44),'vram_address':hex(u(texture+52)),
            'texture_status':hex(u(texture+64)),
            'render_header_valid':(u(texture+8)!=0 and u(texture+12)!=0)}
    return atlas,report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state',type=Path)
    args=parser.parse_args()
    print(json.dumps(font_state(args.state)[1],indent=2))
