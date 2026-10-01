"""Compare native glyph output using a local BIOS. Default is read-only."""
import argparse
from pathlib import Path
import subprocess

from PIL import Image,ImageDraw,ImageFont
from inspect_disc_text import Disc,ROOT
from build_hd_font import plan,BASE
from build_vwf import patched_conversion
from validate_vwf import CPU
import bizin_font


def render(program,bios,payload=None,text='Marionette'):
    cpu=CPU(program)
    indices={}
    if payload:
        at=bizin_font.FONT_SOURCE-0x8c000000;cpu.mem[at:at+len(payload)]=payload
        indices={int.from_bytes(payload[16+i*bizin_font.STRIDE:18+i*bizin_font.STRIDE],'little'):i for i in range(613)}
    cpu.write(0x8c2cd63c,0x8c800000)
    # The older generator's runtime pointer literal; the new generator uses
    # the data global directly and leaves its executable immutable.
    if cpu.read(BASE+0x86a8)==0x8c2cd644:
        cpu.write(BASE+0x86a8,0x8c800000)
    def dimensions():
        cpu.write(cpu.r[6],24,1);cpu.write(cpu.r[6]+1,24,1)
    cpu.stubs.update({0x8c159340:dimensions,0x8c159088:cpu.wait})
    result=Image.new('RGBA',(1200,40),(0,0,0,0));cursor=0
    for index,char in enumerate(text):
        if char==' ':cursor+=40;continue
        code=patched_conversion(ord(char))
        if payload:index=indices[code]
        jis=code.to_bytes(2,'big').decode('cp932').encode('iso2022_jp')
        assert jis[:3]==b'\x1b$B'
        offset=0x100020+0x2880+((jis[3]-33)*94+jis[4]-33)*72
        bitmap=bios[offset:offset+72];assert len(bitmap)==72
        cpu.mem[0x700000:0x700048]=bitmap
        cpu.r[4:7]=[0x8c700000,code,index];cpu.pr=0x8cfffffc
        cpu.run(BASE+0x8494,limit=1000000)
        bearing=cpu.read(0x8c34dbb4+index,1)*2
        advance=cpu.read(0x8c34de28+index,1)*2
        x0=(index%25)*40;y0=(index//25)*40
        for y in range(38):
            for x in range(38):
                value=cpu.read(0x8c800000+((y0+y)*1024+x0+x)*2,2)
                alpha=(value>>12)*17
                pos=cursor+x-bearing
                if alpha and 0<=pos<result.width:
                    result.putpixel((pos,y),(0,0,0,alpha))
        cursor+=advance
    return result.crop((0,0,cursor,40))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bios',type=Path,required=True)
    p.add_argument('--reference-commit',default='afd2741')
    p.add_argument('--write',action='store_true')
    args=p.parse_args()
    d=Disc();entry=next(e for e in d.files if e['path']=='/1ST_READ.BIN')
    original=d.read(entry['lba'],entry['size'])
    source=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),
                                    'show',args.reference_commit+':tools/build_hd_font.py'],cwd=ROOT)
    reference={'__name__':'font_reference'}
    exec(compile(source,'committed-font-reference','exec'),reference)
    old,_=reference['plan'](original);new,_=plan(original)
    bios=args.bios.read_bytes()
    payload,_=bizin_font.asset(new)
    before=render(old,bios);after=render(new,bios,payload)
    assert after.getbbox() and before.getbbox()
    print('Rendered BIOS and Bizin Gothic Bold glyphs through the native generators.')
    if not args.write:
        print('Dry run; no preview written.');return
    words=['Marionette','Shop','Settings','Log Out']
    images=[(render(old,bios,text=word),render(new,bios,payload,word)) for word in words]
    panel=Image.new('RGB',(1050,600),'#f0eee8')
    draw=ImageDraw.Draw(panel);font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
    draw.text((24,16),'0.1.7 — Dreamcast BIOS',fill='#222222',font=font)
    draw.text((530,16),'0.1.8 — Bizin Gothic Bold',fill='#222222',font=font)
    for row,pair in enumerate(images):
        for col,glyphs in enumerate(pair):
            enlarged=glyphs.resize((glyphs.width*2,glyphs.height*2),Image.Resampling.NEAREST)
            panel.paste(enlarged,(24+col*506,60+row*120),enlarged)
    draw.text((24,558),'Native glyph preview; Flycast filtering may change appearance.',fill='#555555',font=font)
    path=ROOT/'work/ui/font-BIOS-vs-Bizin-Gothic-Bold-0.1.8.png'
    panel.save(path);print(path)


if __name__=='__main__':
    main()
