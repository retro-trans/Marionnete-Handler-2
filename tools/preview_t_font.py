"""Preview the t correction through the native glyph generator, without editing screenshots."""
import argparse
import json
import hashlib
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont
from inspect_disc_text import Disc,ROOT
from build_hd_font import plan,VERSION
from preview_hd_font import render
from bizin_font import asset,ASSET_BYTES,STRIDE,CACHED,ASCII


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bios',type=Path,required=True)
    p.add_argument('--write',action='store_true');args=p.parse_args()
    d=Disc();e=next(e for e in d.files if e['path']=='/1ST_READ.BIN')
    program,report=plan(d.read(e['lba'],e['size']))
    folder=ROOT/'work/output/english-0.1.9'
    previous=json.loads((folder/'PATCH-REPORT.json').read_text(encoding='utf-8'))
    assert previous['target_program_sha256']==report['target_program_sha256']
    before=(folder/'ENFONT.BIN').read_bytes()[:ASSET_BYTES];after,metadata=asset(program)
    assert previous['font_asset']['latin_metrics']==metadata['latin_metrics']
    changed=[i for i in range(CACHED+ASCII) if before[16+i*STRIDE:16+(i+1)*STRIDE]!=after[16+i*STRIDE:16+(i+1)*STRIDE]]
    assert len(changed)==2 and before[:16]==after[:16]
    words=['t','Marionette','Settings','Log Out'];pairs=[];bios=args.bios.read_bytes()
    for word in words:
        old=render(program,bios,before,word);new=render(program,bios,after,word)
        assert old.size==new.size and old.tobytes()!=new.tobytes()
        pairs.append((old,new))
    print('Only two t records change; executable and all word advances are identical.',flush=True)
    if not args.write:return
    panel=Image.new('RGB',(1100,540),'#ebe7df');draw=ImageDraw.Draw(panel)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
    draw.text((20,12),'0.1.9',font=font,fill='#151515')
    draw.text((565,12),VERSION+' — corrected t',font=font,fill='#151515')
    for row,pair in enumerate(pairs):
        for col,glyphs in enumerate(pair):
            preview=glyphs.resize((glyphs.width*2,glyphs.height*2),Image.Resampling.NEAREST)
            panel.paste(preview,(20+col*545,48+row*110),preview)
    draw.text((20,500),'Native font preview; Flycast filtering affects the final appearance.',font=font,fill='#555555')
    panel.save(ROOT/'work/ui/font-t-0.1.9-vs-0.1.10.png')
    evidence={'version':VERSION,'executable_identical_to':'0.1.9',
        'target_program_sha256':report['target_program_sha256'],
        'before_font_asset_sha256':hashlib.sha256(before).hexdigest(),
        'after_font_asset_sha256':hashlib.sha256(after).hexdigest(),
        'changed_record_indices':changed,'changed_characters':['cached t','editable ASCII t'],
        'all_other_glyph_records_identical':True,'cached_latin_metrics_identical':True,
        'native_preview_words':words,'word_advances_identical':True,
        'preview':'font-t-0.1.9-vs-0.1.10.png','actual_Flycast_screenshot':False}
    (ROOT/'work/ui/font-t-change-0.1.10.json').write_bytes((json.dumps(evidence,indent=2)+'\n').encode('utf-8'))


if __name__=='__main__':main()
