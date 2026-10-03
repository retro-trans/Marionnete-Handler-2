"""Verify the native sector opener/stream reader against captured Flycast GDFS RAM."""
import argparse
import json
import struct
from pathlib import Path

from inspect_disc_text import Disc,ROOT
from inspect_font_state import read_ram,font_state
from build_hd_font import plan,BASE
from bizin_font import FONT_SOURCE,ASSET_BYTES,asset,MAGIC
from validate_vwf import CPU


def validate(path):
    d=Disc();e=next(e for e in d.files if e['path']=='/1ST_READ.BIN')
    program,report=plan(d.read(e['lba'],e['size']));payload,_=asset(program)
    ram=read_ram(path);c=CPU(program);c.mem[:]=ram
    # Replace only font helpers: keep the real directory, device and handle tables.
    for helper in report['font']['helpers'].values():
        at=helper['offset'];c.mem[at+0x10000:at+0x10000+helper['bytes']]=program[at:at+helper['bytes']]
    c.write(FONT_SOURCE,0)
    c.stubs[0x8c152c90]=c.wait # native library error reporting only
    c.stubs[0x8c010988]=lambda:c.r.__setitem__(0,c.r[1]//c.r[0])
    c.stubs[0x8c010a3c]=lambda:c.r.__setitem__(0,c.r[1]//c.r[0])
    def copy():
        dest,source,size=c.r[4:7]
        assert 0x8c000000<=dest<=0x8d000000-size and 0x8c000000<=source<=0x8d000000-size
        c.mem[dest-0x8c000000:dest-0x8c000000+size]=c.mem[source-0x8c000000:source-0x8c000000+size]
        c.r[0]=dest
    c.stubs[0x8c1712fc]=copy
    # Only the physical sector transfer is simulated; the game stream reader runs.
    extent=payload.ljust(67*2048,b'\0');reads=[]
    def disc_read():
        handle,sectors,dest=c.r[4:7]
        assert c.read(handle+8)==549150 and c.read(handle+16)==67
        index=c.read(handle+20);size=sectors*2048
        assert index+sectors<=67 and dest%32==0
        reads.append({'sector_offset':index,'sectors':sectors,'destination':hex(dest)})
        c.mem[dest-0x8c000000:dest-0x8c000000+size]=extent[index*2048:(index+sectors)*2048]
        c.write(handle+20,index+sectors);c.r[0]=0
    c.stubs[0x8c15471e]=disc_read
    entry=BASE+report['font']['helpers']['bizin_loader']['offset']
    c.run(entry,limit=1000000)
    assert c.r[15]==0x8cf00000 and c.read(FONT_SOURCE)==MAGIC
    at=FONT_SOURCE-0x8c000000;assert c.mem[at:at+ASSET_BYTES]==payload
    assert reads and c.read(0x8c19fef0)==ASSET_BYTES
    assert c.read(c.read(0x8c38f640)+76,2)==0 # actual native close frees handle
    calls=len(reads);c.pr=0x8cfffffc;c.run(entry);assert len(reads)==calls
    _,previous=font_state(path)
    previous.update(bizin_header_before=ram[0x30e644:0x30e654].hex(),
                    bizin_header_address_before='0x8c30e644',
                    font_asset_loaded_before=False)
    return {'saved_state_before':previous,'native_GDFS_dispatcher':hex(0x8c154f04),
            'native_GDFS_open_handle_and_size':True,'native_stream_reader':True,
            'native_close_frees_handle':True,'asset_bytes_identical':True,
            'current_directory_independent':True,'DMA_destination_alignment':32,
            'physical_disc_reads_simulated':reads,'target_program_sha256':report['target_program_sha256']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('state',type=Path)
    p.add_argument('--report',action='store_true');args=p.parse_args()
    result=validate(args.state);print(json.dumps(result,indent=2))
    if args.report:
        path=ROOT/'work/ui/font-loader-0.1.9-validation.json'
        path.write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
