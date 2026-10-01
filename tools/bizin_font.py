"""Bizin Gothic glyph asset and native loader for the English patch."""
import hashlib
from pathlib import Path
import struct

from PIL import Image,ImageDraw,ImageFont
from build_english import prepare_native_cache
from build_vwf import patched_conversion
from sh4_patch import Assembler

FONT_SOURCE=0x8c30e644 # unused tail of the original atlas, beyond VQ scratch
MAGIC=0x4e5a4942
CACHED=613
ASCII=95
STRIDE=192
ASSET_BYTES=16+(CACHED+ASCII)*STRIDE
FONT=Path(__file__).parent/'fonts/bizin-gothic/BizinGothic-Bold.ttf'


def lookup(address):
    a=Assembler(address)
    a.load(0,FONT_SOURCE)
    a.load(1,MAGIC)
    a.emit(0x6202,0x3210)
    a.branch(0x8b00,'absent')
    a.load(0,256)
    a.emit(0x3402)
    a.branch(0x8b00,'ascii')
    a.load(0,CACHED)
    a.emit(0x3502)
    a.branch(0x8900,'absent')
    a.branch(0xa000,'record')
    a.emit(0x6053)
    a.label('ascii')
    a.emit(0xe020,0x3402)
    a.branch(0x8b00,'absent')
    a.emit(0xe07e,0x3406)
    a.branch(0x8900,'absent')
    a.emit(0x6043)
    a.load(1,CACHED-32)
    a.emit(0x301c)
    a.label('record')
    a.load(1,STRIDE)
    a.emit(0x0017,0x001a)
    a.load(1,FONT_SOURCE+16)
    a.emit(0x301c,0x6201,0x622d,0x3240)
    a.branch(0x8b00,'absent')
    a.emit(0x7002,0x6301,0x2338)
    a.branch(0x8900,'absent')
    a.emit(0x70fe,0x000b,0x0009)
    a.label('absent')
    a.emit(0xe000,0x000b,0x0009)
    return a.finish()


def loader(address):
    a=Assembler(address)
    a.emit(0x4f22,0x2f86)
    a.load(8,FONT_SOURCE)
    a.load(1,MAGIC)
    a.emit(0x6082,0x3010)
    a.branch(0x8900,'done')
    a.emit(0xe000,0x2802)
    marker=0xc010c17c
    a.load(4,marker)
    a.load(0,0x8c16acd4)
    a.emit(0x400b,0x0009,0x4011)
    a.branch(0x8b00,'done')
    a.emit(0x6483)
    a.load(5,ASSET_BYTES)
    a.load(0,0x8c16ad34)
    a.emit(0x400b,0x0009,0x6103)
    # Keep read result across close; r8 is preserved by the native API.
    a.emit(0x2f16)
    a.load(0,0x8c16ad2c)
    a.emit(0x400b,0x0009,0x61f6,0x4111)
    a.branch(0x8b00,'invalid')
    a.emit(0x6082)
    a.load(1,MAGIC)
    a.emit(0x3010)
    a.branch(0x8b00,'invalid')
    a.emit(0x5081)
    a.load(1,(STRIDE<<16)|(CACHED+ASCII))
    a.emit(0x3010)
    a.branch(0x8900,'done')
    a.label('invalid')
    a.emit(0xe000,0x2802)
    a.label('done')
    a.emit(0x68f6,0x4f26,0x000b,0x0009)
    code=a.finish()
    return code.replace(struct.pack('<I',marker),struct.pack('<I',address+len(code)))+b'\\ENFONT.BIN\0'


def covered_characters(data):
    """Read Unicode cmap coverage without an extra font dependency."""
    count=struct.unpack_from('>H',data,4)[0]
    tables={data[12+i*16:16+i*16]:struct.unpack_from('>II',data,20+i*16) for i in range(count)}
    offset,_=tables[b'cmap'];entries=struct.unpack_from('>H',data,offset+2)[0]
    covered=set()
    for i in range(entries):
        platform,encoding,relative=struct.unpack_from('>HHI',data,offset+4+i*8)
        if platform not in (0,3):continue
        start=offset+relative;fmt=struct.unpack_from('>H',data,start)[0]
        if fmt==12:
            groups=struct.unpack_from('>I',data,start+12)[0]
            for j in range(groups):
                first,last,glyph=struct.unpack_from('>III',data,start+16+j*12)
                covered.update(range(first+(glyph==0),last+1))
        elif fmt==4:
            segments=struct.unpack_from('>H',data,start+6)[0]//2
            ends=start+14;starts=ends+segments*2+2;deltas=starts+segments*2;ranges=deltas+segments*2
            for j in range(segments):
                last=struct.unpack_from('>H',data,ends+j*2)[0];first=struct.unpack_from('>H',data,starts+j*2)[0]
                delta=struct.unpack_from('>h',data,deltas+j*2)[0];jump=struct.unpack_from('>H',data,ranges+j*2)[0]
                for char in range(first,min(last,65534)+1):
                    glyph=(char+delta)&65535 if not jump else struct.unpack_from('>H',data,ranges+j*2+jump+(char-first)*2)[0]
                    if glyph:covered.add(char)
    return covered


def asset(program):
    _,_,codes,frames=prepare_native_cache(program)
    assert len(codes)==CACHED and len(set(codes))==CACHED
    font_bytes=FONT.read_bytes();coverage=covered_characters(font_bytes)
    reverse={patched_conversion(c):chr(c) for c in range(32,127)}
    fonts={44:ImageFont.truetype(str(FONT),44),35:ImageFont.truetype(str(FONT),35)}
    result=bytearray(struct.pack('<4I',MAGIC,(STRIDE<<16)|(CACHED+ASCII),0,0))
    fallback=[];metrics=[]
    for index,code in enumerate(codes+list(range(32,127))):
        char=reverse.get(code) if index<CACHED else chr(code)
        if char is None:char=code.to_bytes(2,'big').decode('cp932')
        image=Image.new('L',(38,38),0)
        if ord(char) not in coverage:
            result+=struct.pack('<H',code)+bytes(STRIDE-2);fallback.append(hex(code));continue
        latin=char.isascii();font=fonts[44 if latin else 35]
        box=font.getbbox(char,anchor='ls')
        if latin:
            x=3-box[0];baseline=29
            if box[3]+baseline>38:baseline=38-box[3]
            if box[1]+baseline<0:baseline=-box[1]
        else:
            x=(38-(box[2]-box[0]))//2-box[0];baseline=35
            if box[3]+baseline>38:baseline=38-box[3]
            if box[1]+baseline<0:baseline=-box[1]
        assert 0<=x+box[0] and x+box[2]<=38 and 0<=baseline+box[1] and baseline+box[3]<=38,(hex(code),box)
        ImageDraw.Draw(image).text((x,baseline),char,font=font,anchor='ls',fill=255)
        bitmap=bytearray(184)
        for y in range(38):
            for px in range(38):
                if image.getpixel((px,y))>=128:
                    bit=y*38+px;bitmap[bit//8]|=128>>(bit%8)
        mask=image.point(lambda v:255 if v>=128 else 0)
        ink=mask.getbbox()
        result+=struct.pack('<HBBI',code,38,38,0)+bitmap
        if latin and index<CACHED:
            left=min(14,ink[0]) if ink else 14;right=max(22,ink[2]-1) if ink else 22
            metrics.append({'code':hex(code),'character':char,'bearing':left//2,'advance':(right-left)//2+4})
    assert len(result)==ASSET_BYTES
    return bytes(result),{'family':'Bizin Gothic','weight':'Bold','upstream_version':'0.0.4',
        'source_url':'https://github.com/yuru7/bizin-gothic','font_sha256':hashlib.sha256(font_bytes).hexdigest(),
        'asset_sha256':hashlib.sha256(result).hexdigest(),'asset_bytes':len(result),
        'cached_records':CACHED,'editable_ascii_records':ASCII,'cache_frames':frames,
        'missing_glyphs_use_BIOS':fallback,'latin_metrics':metrics,'bitmap_dimensions':[38,38],
        'latin_raster_size':44,'other_raster_size':35,'threshold':128,'texture_replacement':False}


def validate(program,report,payload):
    """Execute the loader, lookup and every font record in the SH-4 harness."""
    from validate_vwf import CPU
    from build_vwf import BASE
    cpu=CPU(program);events=[]
    entry=BASE+report['font']['helpers']['bizin_loader']['offset']
    def open_file():
        pos=cpu.r[4]-0x8c000000
        name=bytes(cpu.mem[pos:pos+12]).split(b'\0')[0]
        assert name==b'\\ENFONT.BIN',name
        events.append('open');cpu.r[0]=0
    def read_file():
        assert cpu.r[4:6]==[FONT_SOURCE,ASSET_BYTES]
        cpu.mem[FONT_SOURCE-0x8c000000:FONT_SOURCE-0x8c000000+len(payload)]=payload
        events.append('read');cpu.r[0]=0
    def close_file():events.append('close');cpu.r[0]=0
    cpu.stubs.update({0x8c16acd4:open_file,0x8c16ad34:read_file,0x8c16ad2c:close_file})
    cpu.r[8]=0x12345678;cpu.run(entry)
    assert events==['open','read','close'] and cpu.r[8]==0x12345678 and cpu.r[15]==0x8cf00000
    cpu.pr=0x8cfffffc;cpu.run(entry);assert len(events)==3
    # Open failure, read failure and bad header cannot leave a valid font.
    for failure in ('open','read','header'):
        cpu.write(FONT_SOURCE,0)
        cpu.stubs[0x8c16acd4]=lambda:cpu.r.__setitem__(0,0xffffffff if failure=='open' else 0)
        def fail_read():
            read_file()
            if failure=='read':cpu.r[0]=0xffffffff
            if failure=='header':cpu.write(FONT_SOURCE+4,0)
        cpu.stubs[0x8c16ad34]=fail_read
        cpu.pr=0x8cfffffc;cpu.run(entry)
        assert cpu.read(FONT_SOURCE)==0 and cpu.r[15]==0x8cf00000
    cpu.mem[FONT_SOURCE-0x8c000000:FONT_SOURCE-0x8c000000+len(payload)]=payload
    cpu.write(0x8c2cd63c,0x8c800000)
    lookup_entry=BASE+report['font']['helpers']['bizin_lookup']['offset']
    atlas=bytearray(0x200000);native_metrics={};records=[]
    for index in range(CACHED+ASCII):
        record=payload[16+index*STRIDE:16+(index+1)*STRIDE]
        code,width,height=struct.unpack_from('<HBB',record)
        cache_index=index if index<CACHED else 7
        cpu.r[4:6]=[code,cache_index];cpu.pr=0x8cfffffc;cpu.run(lookup_entry)
        expected=FONT_SOURCE+16+index*STRIDE if width else 0
        assert cpu.r[0]==expected,(index,hex(cpu.r[0]),hex(expected))
        if not width:continue
        cpu.r[4:7]=[0x8c700000,code,cache_index];cpu.pr=0x8cfffffc
        cpu.run(BASE+0x8494,limit=1000000)
        assert cpu.r[15]==0x8cf00000
        size=38 if index<CACHED else 42
        x0=(index%25)*40 if index<CACHED else 600+7*44
        y0=(index//25)*40 if index<CACHED else 960
        ink=[]
        for y in range(size):
            for x in range(size):
                bit=(y*height//size)*width+x*width//size
                value=0xffff if record[8+bit//8]&(128>>(bit%8)) else 0
                address=((y0+y)*1024+x0+x)*2
                assert cpu.read(0x8c800000+address,2)==value,(index,x,y)
                if index<CACHED:
                    atlas[address:address+2]=struct.pack('<H',value)
                    if value:ink.append(x)
        if index<CACHED:
            left=min([14]+ink);right=max([22]+ink)
            bearing=cpu.read(0x8c34dbb4+index,1);advance=cpu.read(0x8c34de28+index,1)
            assert (bearing,advance)==(left//2,(right-left)//2+4)
            native_metrics[code]=(bearing,advance)
        records.append(index)
    for code,index in ((0x8260,613),(0x8260,1),(31,0),(127,0)):
        cpu.r[4:6]=[code,index];cpu.pr=0x8cfffffc;cpu.run(lookup_entry);assert cpu.r[0]==0
    print('Bizin Gothic: native loader failure paths and all 708 glyph records verified.',flush=True)
    return {'loader_read_bytes':ASSET_BYTES,'loader_idempotent':True,'loader_failure_paths':3,
            'record_lookups':CACHED+ASCII,'native_glyphs_pixel_verified':len(records),
            'all_cached_widths_verified':len(native_metrics)},bytes(atlas),native_metrics
