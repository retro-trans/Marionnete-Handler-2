"""Built-in 2x cached font atlas, preserving the 0.1.4 English text.

This retains the BIOS typeface, but samples it into 38-pixel glyphs rather
than reducing it to 19 pixels. It is a ROM patch, not a Flycast texture pack.
Default is a plan; --validate runs the limited native harness; --build writes.
"""
import argparse
import json
import os
from pathlib import Path
import struct

from inspect_disc_text import Disc, ROOT
from full_english import plan as english_plan, digest, merged
from sh4_patch import Assembler, pc_load
from build_vwf import BASE, write_track, gdi
from build_full_english import validate, verify_track
from validate_vwf import CPU

VERSION='0.1.7'
FONT_BYTES=0x200000
VQ_BYTES=2048+1024*1024//4


def vq_upload(address):
    """Twiddle, then encode a fixed 256-entry ARGB4444 VQ codebook.

    The unused original atlas is scratch. Zero/D/E/F alpha levels are kept;
    C alpha rounds up to D. The captured 613-glyph atlas uses only 0/D/F.
    """
    a=Assembler(address)
    a.emit(0x4f22,0x2f86,0x2f96,0x2fa6,0x2fb6,0x6843)
    a.load(0,0x8c16dc04)
    a.emit(0x400b,0x0009)
    a.load(3,0x8c2cd644)
    color_marker=0xc010a17a
    a.load(2,color_marker)
    a.emit(0xeb00)
    a.label('palette')
    a.emit(0x66b3,0xe704)
    a.label('color')
    a.emit(0x6063,0xc903,0x4000,0x012d,0x2311,0x7302,
           0x4601,0x4601,0x4710)
    a.branch(0x8b00,'color')
    a.emit(0x7b01)
    a.load(1,256)
    a.emit(0x3b10)
    a.branch(0x8b00,'palette')
    a.emit(0x6983,0x7906,0x6a33,0x7208)
    a.load(11,1024*1024//4)
    a.label('block')
    a.emit(0xe600,0xe704)
    a.label('pixel')
    a.emit(0x6091,0x79fe)
    # Word sign-extension is removed before extracting the two alpha bits.
    a.emit(0x600d,0x4019,0x4009,0x4009,0x002c)
    a.emit(0x4608,0x260b,0x4710)
    a.branch(0x8b00,'pixel')
    a.emit(0x2a60,0x7a01,0x7910,0x4b10)
    a.branch(0x8b00,'block')
    a.load(9,0x8c2cd644)
    a.load(11,VQ_BYTES//4)
    a.emit(0x6383)
    a.label('copy')
    a.emit(0x6196,0x2312,0x7304,0x4b10)
    a.branch(0x8b00,'copy')
    a.emit(0x6483)
    a.load(5,VQ_BYTES)
    a.load(0,0x8c15b892)
    a.emit(0x400b,0x0009)
    a.emit(0x6bf6,0x6af6,0x69f6,0x68f6,0x4f26,0x000b,0x0009)
    # Reserve the color table after the literal pool; repair the load fixup.
    first=a.finish()
    assert first.count(struct.pack('<I',color_marker))==1
    return first.replace(struct.pack('<I',color_marker),
                         struct.pack('<I',address+len(first)))+struct.pack('<4H',0,0xdfff,0xefff,0xffff)+bytes([0]+[1]*13+[2,3])


def initialize(address,encoder=0x8c16dc04):
    a=Assembler(address)
    # Entered by JMP while the original font init's PR is already on its stack.
    a.load(4,FONT_BYTES)
    a.load(0,0x8c15cf2a)
    a.emit(0x400b,0x0009,0x2008)
    a.branch(0x8900,'failed')
    a.emit(0x6503)
    for dest in (0x8c2cd63c,BASE+0x75c8,BASE+0x77e4):
        a.load(1,dest)
        a.emit(0x2102)
    # Clear the full persistent atlas, including the 24-pixel right/bottom gap.
    a.emit(0x6303,0xe100)
    a.load(2,FONT_BYTES//4)
    a.label('clear')
    a.emit(0x2312,0x7304,0x4210)
    a.branch(0x8b00,'clear')
    a.load(0,0x8c2cd640)
    a.emit(0x6402)
    a.load(6,1024)
    a.load(0,encoder)
    a.emit(0x400b,0x0009)
    a.load(1,BASE+0x793e)
    a.emit(0x412b,0x0009)
    a.label('failed')
    a.emit(0xe000)
    a.load(1,BASE+0x7992)
    a.emit(0x412b,0x0009)
    return a.finish()


def coordinates(address):
    a=Assembler(address)
    a.emit(0x4f22,0x2f86,0x2f96,0x6843)
    a.load(0,0x8c010234)
    a.emit(0xe519,0x400b,0x0009,0x6903,0x6403)
    # x = (index % 25) * 40.
    a.emit(0x4908,0x394c,0x4908,0x4900,0x6483)
    a.load(0,0x8c0100fc)
    a.emit(0xe519,0x400b,0x0009,0x6103,0x4108,0x310c,0x4108,0x4100)
    a.emit(0x6093,0x69f6,0x68f6,0x4f26,0x000b,0x0009)
    return a.finish()


def metrics(address):
    a=Assembler(address)
    # r4=min x, r5=max x, r6=cache index. Convert ink extents to UI pixels.
    a.emit(0x3548,0x4501,0x7504,0x4401)
    a.load(0,0x8c34dbb4)
    a.emit(0x0644)
    a.load(0,0x8c34de28)
    a.emit(0x0654,0x000b,0x0009)
    return a.finish()


def glyph(address,coordinate_address,metric_address):
    """Fill every destination texel by reading its corresponding BIOS bit."""
    a=Assembler(address)
    for register in range(14,7,-1):
        a.emit(0x2f06|(register<<4))
    a.emit(0x4f22,0x7fe8,0x6e43,0x1f61,0x1f54)
    # Locals: dimensions, index, min/max x, original code, source-row bit index.
    a.load(0,256)
    a.emit(0x3502)
    a.branch(0x8b00,'editable')
    a.emit(0xed26,0xe404,0x66f3)
    a.load(0,0x8c159340)
    a.emit(0x400b,0x0009,0xe404,0x55f4)
    a.load(0,0x8c159088)
    a.emit(0x400b,0x0009,0x6ce3,0x3c0c,0x54f1)
    a.load(0,coordinate_address)
    a.emit(0x400b,0x0009)
    a.branch(0xa000,'position')
    a.emit(0x0009)
    a.label('editable')
    a.emit(0xed2a,0xe406,0x66f3)
    a.load(0,0x8c159340)
    a.emit(0x400b,0x0009,0x6ce3,0x50f1,0xe12c,0x0017,0x001a)
    a.load(1,600)
    a.emit(0x301c)
    a.load(1,960)
    a.label('position')
    a.emit(0x4118,0x4108,0x4100,0x4000)
    a.load(2,0x8c2cd63c)
    a.emit(0x6222,0x320c,0x321c,0x6b23,0x6af0,0x6aac,
           0xe00e,0x1f02,0xe016,0x1f03,0xe900)
    a.label('row')
    a.emit(0xe001,0x03fc,0x633c,0x0397,0x041a,0x65d3)
    a.load(0,0x8c0100fc)
    a.emit(0x400b,0x0009,0x00a7,0x001a,0x1f05,0xe800)
    a.label('column')
    a.emit(0x08a7,0x041a,0x65d3)
    a.load(0,0x8c0100fc)
    a.emit(0x400b,0x0009,0x51f5,0x301c,0x6103,0xc907)
    mask_marker=0xc010b17b
    a.load(2,mask_marker)
    a.emit(0x022c,0x4109,0x4101,0x31cc,0x6110,0x2129,0x2118)
    a.branch(0x8900,'blank')
    a.load(2,0xffff)
    a.emit(0x50f2,0x3087)
    a.branch(0x8b00,'maximum')
    a.emit(0x1f82)
    a.label('maximum')
    a.emit(0x50f3,0x3807)
    a.branch(0x8b00,'write')
    a.emit(0x1f83)
    a.branch(0xa000,'write')
    a.emit(0x0009)
    a.label('blank')
    a.emit(0xe200)
    a.label('write')
    a.emit(0x6083,0x4000,0x0b25,0x7801,0x38d3)
    a.branch(0x8b00,'column')
    a.load(0,2048)
    a.emit(0x3b0c,0x7901,0x39d3)
    a.branch(0x8b00,'row')
    a.emit(0x60d3,0x8826)
    a.branch(0x8b00,'done')
    a.emit(0x54f2,0x55f3,0x56f1)
    a.load(0,metric_address)
    a.emit(0x400b,0x0009)
    a.label('done')
    a.emit(0x7f18,0x4f26)
    for register in range(8,15):
        a.emit(0x60f6|(register<<8))
    a.emit(0x000b,0x0009)
    code=a.finish()
    return code.replace(struct.pack('<I',mask_marker),struct.pack('<I',address+len(code)))+bytes(128>>i for i in range(8))


def plan(original):
    target,report=english_plan(original)
    b=bytearray(target)
    free=[list(s) for s in report['allocation']['free_fragments']]
    changes=list(report['changed_regions'])
    helpers={}
    for name,build in [('vq_upload',vq_upload),
                       ('initialize',lambda address:initialize(address,BASE+helpers['vq_upload']['offset'])),
                       ('coordinates',coordinates),('metrics',metrics)]:
        choices=[]
        for i,(start,end) in enumerate(free):
            aligned=(start+3)&~3
            blob=build(BASE+aligned)
            if aligned+len(blob)<=end:
                choices.append((end-aligned-len(blob),i,aligned,blob))
        if not choices:
            raise ValueError('No verified translation-bank fragment fits '+name)
        _,i,at,blob=min(choices)
        b[at:at+len(blob)]=blob
        free[i][0]=at+len(blob)
        changes.append((at,at+len(blob)))
        helpers[name]={'offset':at,'bytes':len(blob)}
    def patch(at,old,new):
        if b[at:at+len(old)]!=old:
            raise ValueError('Font source guard failed at '+hex(at))
        if len(old)!=len(new):
            raise ValueError('Patch changes executable size')
        b[at:at+len(new)]=new
        changes.append((at,at+len(new)))
    def word(at,old,new):
        patch(at,struct.pack('<H',old),struct.pack('<H',new))
    def literal(at,old,new):
        patch(at,struct.pack('<I',old),struct.pack('<I',new))
    # All three font upload buffers and texture dimensions, including VRAM init.
    for at in (0x75bc,0x77d8,0x79a0):
        literal(at,0x80000,FONT_BYTES)
    for at in (0x75c4,0x77e0,0x79a8):
        literal(at,512,1024)
    # Descriptor format: ARGB4444 VQ rather than uncompressed twiddled pixels.
    literal(0x79ac,0x102,0x302)
    for at in (0x75cc,0x77e8):
        literal(at,0x8c16dc04,BASE+helpers['vq_upload']['offset'])
    entry=0x7930
    hook=struct.pack('<4HI',pc_load(0,BASE+entry,BASE+entry+8),0x402b,0x0009,0x0009,BASE+helpers['initialize']['offset'])
    patch(entry,target[entry:entry+12],hook)
    # Replace the original forward pixel plotting loop with inverse sampling.
    # Reuse only its own verified code/literal span; keep executable size fixed.
    entry=0x8494
    blob=glyph(BASE+entry,BASE+helpers['coordinates']['offset'],
               BASE+helpers['metrics']['offset'])
    assert len(blob)<=0x86bc-entry
    patch(entry,target[entry:0x86bc],blob+b'\x09\x00'*((0x86bc-entry-len(blob))//2))
    helpers['glyph']={'offset':entry,'bytes':len(blob)}
    report.update(version=VERSION,target_program_sha256=digest(b),changed_regions=merged(changes))
    report['allocation']['remaining_fragment_bytes']=sum(z-a for a,z in free)
    report['allocation']['free_fragments']=free
    report['allocation']['font_helper_bytes']=sum(h['bytes'] for h in helpers.values())
    report['font']={'type':'built_in_BIOS_supersampling','texture_before':[512,512],
        'texture_after':[1024,1024],'cached_cell_before':20,'cached_cell_after':40,
        'glyph_before':19,'glyph_after':38,'display_quad_pixels':19,
        'original_source_font':'BIOS 24x24 bitmap; no new vector typeface',
        'persistent_ram_added_bytes':FONT_BYTES,'temporary_upload_bytes':FONT_BYTES,
        'vram_texture_bytes':VQ_BYTES,'helpers':helpers,
        'compression':'native ARGB4444 VQ, fixed 256-entry codebook',
        'sampling':'inverse nearest-neighbor; all destination pixels filled',
        'small_font':'unchanged 12-pixel font','texture_replacement':False,
        'allocation_failure':'font init returns failure and retries; no writes to original undersized buffer'}
    return bytes(b),report


def validate_vq(target,report,atlas=None):
    cpu=CPU(target)
    # All 256 fixed codebook patterns, tiled through the complete input buffer.
    colors=(0,0xdfff,0xefff,0xffff)
    if atlas is None:
        twiddled=b''.join(struct.pack('<4H',*(colors[(i>>(2*j))&3] for j in range(4)))
                          for i in range(256))*1024
        expected=bytes(range(256))*1024
    else:
        assert len(atlas)==FONT_BYTES
        def spread(v):
            return sum(((v>>i)&1)<<(2*i) for i in range(10))
        bits=[spread(v) for v in range(1024)]
        twiddled=bytearray(FONT_BYTES)
        for y in range(1024):
            for x in range(1024):
                source=(y*1024+x)*2;dest=(bits[y]|bits[x]<<1)*2
                twiddled[dest:dest+2]=atlas[source:source+2]
        alpha_codes=[0]+[1]*13+[2,3]
        expected=bytes(sum(alpha_codes[struct.unpack_from('<H',twiddled,i+j*2)[0]>>12]<<(j*2)
                           for j in range(4)) for i in range(0,FONT_BYTES,8))
    cpu.mem[0x400000:0x400000+FONT_BYTES]=twiddled
    cpu.stubs[0x8c16dc04]=cpu.wait
    flushed=[]
    def flush():
        assert cpu.r[4:6]==[0x8c400000,VQ_BYTES]
        flushed.append(tuple(cpu.r[4:6]))
    cpu.stubs[0x8c15b892]=flush
    cpu.r[4]=0x8c400000;cpu.r[5]=0x8c800000;cpu.r[6]=1024
    cpu.r[8:12]=[0x1111,0x2222,0x3333,0x4444]
    cpu.run(BASE+report['font']['helpers']['vq_upload']['offset'],limit=30000000)
    assert cpu.r[15]==0x8cf00000 and cpu.r[8:12]==[0x1111,0x2222,0x3333,0x4444]
    assert len(flushed)==1
    actual=cpu.mem[0x400000:0x400000+VQ_BYTES]
    assert actual[:2048]==b''.join(struct.pack('<4H',*(colors[(i>>(2*j))&3] for j in range(4)))
                                   for i in range(256))
    assert actual[2048:]==expected
    decoded=b''.join(actual[i*8:i*8+8] for i in actual[2048:])
    exact=decoded==twiddled
    if atlas is not None:
        assert exact,'Captured real font must survive compression without pixel changes'
    print('Native VQ encoder: complete atlas round trip, '+('captured BIOS font' if atlas is not None else 'all 256 patterns')+'.',flush=True)
    return {'encoded_bytes':VQ_BYTES,'blocks_verified':262144,'pixels_identical':exact,
            'captured_font':atlas is not None,'palette_alpha_levels':[0,13,14,15],
            'alpha_12_policy':'round up to 13'}


def validate_font(original,target,report):
    cpu=CPU(target)
    allocations=[];uploads=[]
    def allocate():
        assert cpu.r[4]==FONT_BYTES
        cpu.r[0]=0x8c400000 if not allocations else 0x8c800000
        allocations.append(cpu.r[0])
    def upload():
        assert (cpu.r[4],cpu.r[5],cpu.r[6])==(0x8c400000,0x8c800000,1024)
        uploads.append(tuple(cpu.r[4:7]))
    def bios():
        cpu.r[0]=0x8c700000
    cpu.stubs.update({0x8c0151cc:cpu.wait,0x8c15cf2a:allocate,
        0x8c1594ec:bios,
        0x8c16dc04:upload,0x8c16c1ca:lambda:cpu.r.__setitem__(0,1),
        0x8c15b892:cpu.wait,
        0x8c15cff8:cpu.wait})
    cpu.mem[0x800000:0xa00000]=b'\xa5'*FONT_BYTES
    cpu.run(BASE+0x7820,limit=30000000)
    assert cpu.r[0]!=0 and cpu.r[15]==0x8cf00000
    assert cpu.mem[0x800000:0xa00000]==bytes(FONT_BYTES)
    assert allocations==[0x8c400000,0x8c800000] and len(uploads)==1,(allocations,uploads)
    assert cpu.read(0x8c2cd63c)==0x8c800000
    assert [cpu.read(0x8c34d6a4+i*4) for i in (1,4,5)]==[0x3020000,1024,1024]
    assert cpu.mem[0x400800:0x400000+VQ_BYTES]==bytes(VQ_BYTES-2048)
    for offset in (0x75c8,0x77e4):
        assert cpu.read(BASE+offset)==0x8c800000
    print('Native font initialization: 1024x1024, cleared allocation, matched upload.',flush=True)
    # Real BIOS lookup is stubbed; real cache placement/resampling/pixel writer run.
    def dimensions():
        size=32 if cpu.r[4]==6 else 24
        cpu.write(cpu.r[6],size,1);cpu.write(cpu.r[6]+1,size,1)
    cpu.stubs.update({0x8c159340:dimensions,0x8c159088:cpu.wait})
    # Native integer helpers clobber r1-r3; do not hide register-lifetime bugs.
    def integer_helper(modulo=False):
        value=cpu.r[4]%cpu.r[5] if modulo else cpu.r[4]//cpu.r[5]
        cpu.r[1:4]=[0xa1a1a1a1,0xb2b2b2b2,0xc3c3c3c3]
        cpu.r[0]=value
    cpu.stubs[0x8c0100fc]=integer_helper
    cpu.stubs[0x8c010234]=lambda:integer_helper(True)
    bitmap=bytearray(72)
    for y in range(24):
        for x in range(24):
            if x in (4,5,16,17) or (y in (4,5,12,13) and 4<=x<=17):
                bit=y*24+x;bitmap[bit//8]|=128>>(bit%8)
    cpu.mem[0x700000:0x700048]=bitmap
    writes=[]
    original_write=cpu.write
    def guarded(address,value,size=4):
        if 0x8c800000<=address<0x8ca00000:
            writes.append(address)
        else:
            assert (0x8c34dbb4<=address<0x8c34dbb4+613 or
                    0x8c34de28<=address<0x8c34de28+613 or
                    0x8cefff00<=address<=0x8cf00000),hex(address)
        original_write(address,value,size)
    cpu.write=guarded
    sampled=[]
    for index in (0,24,25,612):
        writes.clear();cpu.r[4]=0x8c700000;cpu.r[5]=0x8260;cpu.r[6]=index
        cpu.pr=0x8cfffffc
        cpu.run(BASE+0x8494,limit=1000000)
        assert cpu.r[15]==0x8cf00000 and writes
        x0=(index%25)*40;y0=(index//25)*40
        for address in writes:
            pixel=(address-0x8c800000)//2
            y,x=divmod(pixel,1024)
            assert x0<=x<=x0+38 and y0<=y<=y0+38,(index,x,y,x0,y0)
        bearing=cpu.read(0x8c34dbb4+index,1);advance=cpu.read(0x8c34de28+index,1)
        assert 0<=bearing<19 and 4<=advance<=23
        assert any(cpu.read(0x8c800000+(y*1024+x)*2,2)&0xf000
                   for y in range(y0,y0+39) for x in range(x0,x0+39))
        assert len(writes)==38*38
        for y in range(38):
            for x in range(38):
                bit=(y*24//38)*24+x*24//38
                expected=0xffff if bitmap[bit//8]&(128>>(bit%8)) else 0
                assert cpu.read(0x8c800000+((y0+y)*1024+x0+x)*2,2)==expected,(index,x,y)
        sampled.append({'index':index,'bearing':bearing,'advance':advance,'pixel_writes':len(writes)})
    print('Native glyph resampling: first/last columns and last cache slot stay in bounds.',flush=True)
    # Regenerating a glyph must also erase its previous ink.
    cpu.mem[0x700000:0x700048]=bytes(72)
    cpu.r[4]=0x8c700000;cpu.r[5]=0x8260;cpu.r[6]=0;cpu.pr=0x8cfffffc
    cpu.run(BASE+0x8494,limit=1000000)
    assert all(cpu.read(0x8c800000+(y*1024+x)*2,2)==0 for y in range(38) for x in range(38))
    # The eight editable-name slots share this atlas's bottom row.
    editable=bytearray(128)
    for y in range(32):
        for x in range(32):
            if x==12 or y==20:
                bit=y*32+x;editable[bit//8]|=128>>(bit%8)
    cpu.mem[0x700000:0x700080]=editable
    writes.clear();cpu.r[4]=0x8c700000;cpu.r[5]=65;cpu.r[6]=7
    cpu.pr=0x8cfffffc;cpu.run(BASE+0x8494,limit=1000000)
    for address in writes:
        y,x=divmod((address-0x8c800000)//2,1024)
        assert 908<=x<=950 and 960<=y<=1002,(x,y)
    assert writes and cpu.r[15]==0x8cf00000
    assert len(writes)==42*42
    for y in range(42):
        for x in range(42):
            bit=(y*32//42)*32+x*32//42
            expected=0xffff if editable[bit//8]&(128>>(bit%8)) else 0
            assert cpu.read(0x8c800000+((960+y)*1024+908+x)*2,2)==expected,(x,y)
    # Exhaust every indexed coordinate without rendering every BIOS bitmap.
    coords=BASE+report['font']['helpers']['coordinates']['offset']
    for index in range(613):
        cpu.r[4]=index;cpu.pr=0x8cfffffc;cpu.run(coords)
        assert (cpu.r[0],cpu.r[1])==((index%25)*40,(index//25)*40)
        assert cpu.r[15]==0x8cf00000
    # Allocation failure must not touch an undersized font buffer.
    failed=CPU(target)
    failed.stubs[0x8c15cf2a]=failed.wait
    helper=BASE+report['font']['helpers']['initialize']['offset']
    failed.r[15]-=4;failed.write(failed.r[15],failed.pr)
    failed.run(helper)
    assert failed.r[0]==0 and failed.r[15]==0x8cf00000
    assert failed.read(0x8c2cd63c)==0
    assert failed.mem[0x10000+0x8494:0x10000+0x86bc]==target[0x8494:0x86bc]
    return {'native_font_init':True,'cached_coordinate_cases':613,
        'native_resampling_cases':sampled,'allocation_failure_verified':True,
        'editable_name_slot_bounds_verified':True,
        'all_destination_pixels_verified':True,'glyph_regeneration_clears_old_ink':True,
        'bios_bitmap_simulated':True,'actual_Flycast_playtest':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validate',action='store_true')
    p.add_argument('--build',action='store_true')
    p.add_argument('--font-state',type=Path,help='Validate compression against a captured real BIOS font atlas')
    args=p.parse_args()
    disc=Disc();e=next(e for e in disc.files if e['path']=='/1ST_READ.BIN')
    original=disc.read(e['lba'],e['size'])
    target,report=plan(original)
    print(json.dumps(report['font'],indent=2))
    if args.validate or args.build:
        report['font_validation']=validate_font(original,target,report)
        report['font_validation']['vq_patterns']=validate_vq(target,report)
        if args.font_state:
            from inspect_font_state import font_state
            atlas,evidence=font_state(args.font_state)
            report['font_validation']['reported_blank_state']=evidence
            report['font_validation']['vq_captured_font']=validate_vq(target,report,atlas)
        report['validation']=validate(original,target,report)
    if args.build:
        folder=ROOT/'work'/'output'/('english-'+VERSION)
        folder.mkdir(parents=True,exist_ok=False)
        track=folder/('Marionette Handler 2 (Japan) (Track 17) English '+VERSION+'.bin')
        write_track(disc,e,original,target,track)
        name='Marionette Handler 2 English '+VERSION
        gdi(disc,track,folder/(name+'.gdi'))
        cue=next(ROOT.glob('*.cue')).read_text(encoding='utf-8')
        for source in sorted(ROOT.glob('*Track*.bin')):
            relative=Path(os.path.relpath(str(track if '(Track 17)' in source.name else source),str(folder))).as_posix()
            cue=cue.replace('"'+source.name+'"','"'+relative+'"')
        (folder/(name+'.cue')).write_text(cue,encoding='utf-8')
        verify_track(disc,e,original,target,report,folder)
        for path in (folder/'PATCH-REPORT.json',ROOT/'work'/'ui'/('english_'+VERSION+'_inventory.json')):
            path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('Saved built-in font test image:',folder)
    else:
        print('Dry run; no image written.')


if __name__=='__main__':
    main()
