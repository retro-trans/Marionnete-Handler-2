"""Add the embedded font to guarded unused ISO space; preserve other sectors."""
import hashlib
import shlex
import shutil
import struct

from cdrom_sector import regenerate
from inspect_disc_text import Disc,ROOT

FONT_LBA=549000
ROOT_LBA=45020


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def change_sector(disc,path,lba,payload):
    assert len(payload)==2048
    start,end,_=next(t for t in disc.tracks if t[0]<=lba<t[1])
    offset=(lba-start)*2352
    with path.open('r+b') as stream:
        stream.seek(offset);original=stream.read(2352)
        assert regenerate(original)==original
        sector=bytearray(original);sector[16:2064]=payload
        stream.seek(offset);stream.write(regenerate(sector))


def replace_file(disc,entry,path,content):
    """Patch a same-length ISO asset, preserving its last-sector padding."""
    assert len(content)==entry['size']
    for offset in range(0,len(content),2048):
        lba=entry['lba']+offset//2048
        chunk=content[offset:offset+2048]
        old=disc.read(lba,2048)
        payload=chunk+old[len(chunk):]
        if payload!=old:change_sector(disc,path,lba,payload)


def embed(disc,payload,folder,track17,version):
    # Include the original notices with the glyph data inside the disc image.
    notices=b'\nFont source: Bizin Gothic Bold v0.0.4\nhttps://github.com/yuru7/bizin-gothic\n'
    for path in sorted((ROOT/'tools/fonts/bizin-gothic').glob('*LICENSE')):
        notices+=b'\n'+path.name.encode('ascii')+b'\n'+path.read_bytes()+b'\n'
    content=payload+notices
    sectors=(len(content)+2047)//2048
    end=next(t[1] for t in disc.tracks if t[0]<=FONT_LBA<t[1])
    assert FONT_LBA+sectors<=end
    assert FONT_LBA+sectors<=45000+struct.unpack_from('<I',disc.read(45016,2048),80)[0]
    assert all(e['lba']+(e['size']+2047)//2048<=FONT_LBA or e['lba']>=FONT_LBA+sectors for e in disc.files)
    assert disc.read(FONT_LBA,sectors*2048)==bytes(sectors*2048),'Font area is occupied'
    directory=disc.read(ROOT_LBA,2048);entries=[];offset=0
    while directory[offset]:
        length=directory[offset];entries.append(directory[offset:offset+length]);offset+=length
    assert not any(e[33:33+e[32]]==b'ENFONT.BIN;1' for e in entries)
    name=b'ENFONT.BIN;1';record=bytearray(33+len(name)+(len(name)%2==0))
    record[0]=len(record)
    record[2:10]=struct.pack('<I',FONT_LBA)+struct.pack('>I',FONT_LBA)
    record[10:18]=struct.pack('<I',len(content))+struct.pack('>I',len(content))
    record[18:25]=entries[2][18:25]
    record[28:32]=b'\x01\0\0\x01';record[32]=len(name);record[33:33+len(name)]=name
    entries.append(bytes(record));entries=entries[:2]+sorted(entries[2:],key=lambda e:e[33:33+e[32]])
    new_root=b''.join(entries);assert len(new_root)<=2048
    track3=folder/('Marionette Handler 2 (Japan) (Track 03) English '+version+'.bin')
    source3=next(t[2] for t in disc.tracks if t[0]<=ROOT_LBA<t[1])
    shutil.copyfile(source3,track3)
    change_sector(disc,track3,ROOT_LBA,new_root.ljust(2048,b'\0'))
    padded=content.ljust(sectors*2048,b'\0')
    for i in range(sectors):change_sector(disc,track17,FONT_LBA+i,padded[i*2048:(i+1)*2048])
    (folder/'ENFONT.BIN').write_bytes(content)
    return track3,{'file':'/ENFONT.BIN','lba':FONT_LBA,'file_bytes':len(content),'sectors':sectors,
                   'runtime_read_bytes':len(payload),'includes_font_license_notices':True,
                   'sha256':hashlib.sha256(content).hexdigest(),'root_directory_lba':ROOT_LBA}


def verify(disc,entry,program,track3,track17,folder,report):
    patched=Disc.__new__(Disc)
    replacements={3:track3,17:track17}
    patched.tracks=[(a,z,replacements.get(int(__import__('re').search(r'Track (\d+)',p.name).group(1)),p)) for a,z,p in disc.tracks]
    patched.starts=disc.starts
    files=list(patched.walk(ROOT_LBA,2048));old={e['path']:e for e in disc.files}
    assert all(e==old[e['path']] for e in files if e['path']!='/ENFONT.BIN')
    assert len(files)==len(disc.files)+1
    font=next(e for e in files if e['path']=='/ENFONT.BIN')
    assert patched.read(font['lba'],font['size'])==(folder/'ENFONT.BIN').read_bytes()
    assert patched.read(entry['lba'],entry['size'])==program
    textures=report.get('ui_texture_patches',[])
    for texture in textures:
        asset=old[texture['file']]
        assert asset['lba']==texture['lba'] and asset['size']==texture['size']
        assert hashlib.sha256(patched.read(asset['lba'],asset['size'])).hexdigest()==texture['target_sha256']
    summaries=[]
    for number,path in replacements.items():
        start,_,source=next(t for t in disc.tracks if int(__import__('re').search(r'Track (\d+)',t[2].name).group(1))==number)
        assert path.stat().st_size==source.stat().st_size
        changed=[]
        with source.open('rb') as before,path.open('rb') as after:
            index=0
            while True:
                a=before.read(2352*2048);b=after.read(2352*2048)
                if not a:assert not b;break
                if a!=b:
                    for pos in range(0,len(a),2352):
                        first=a[pos:pos+2352];second=b[pos:pos+2352]
                        if first==second:continue
                        lba=start+index+pos//2352;changed.append(lba)
                        assert regenerate(second)==second,(number,lba)
                        if number==3:assert lba==ROOT_LBA
                        elif entry['lba']<=lba<entry['lba']+(len(program)+2047)//2048:
                            offset=(lba-entry['lba'])*2048;chunk=program[offset:offset+2048]
                            assert second[16:16+len(chunk)]==chunk
                            assert second[16+len(chunk):2064]==first[16+len(chunk):2064]
                        elif FONT_LBA<=lba<FONT_LBA+report['font_disc']['sectors']:
                            pass
                        else:
                            asset=next((t for t in textures if t['lba']<=lba<t['lba']+(t['size']+2047)//2048),None)
                            assert asset is not None,(number,lba)
                            remaining=min(2048,asset['size']-(lba-asset['lba'])*2048)
                            assert second[16+remaining:2064]==first[16+remaining:2064]
                index+=len(a)//2352
        summaries.append({'track':number,'changed_sectors':len(changed),'changed_lbas':changed,
                          'unchanged_sectors_byte_identical':True,'EDC_ECC_verified':True,
                          'source_sha256':sha(source),'target_sha256':sha(path)})
    rows=next(folder.glob('*.gdi')).read_text(encoding='utf-8').splitlines()
    assert rows[0]=='17' and len(rows)==18
    for row in rows[1:]:
        fields=shlex.split(row);number=int(fields[0]);path=(folder/fields[4]).resolve()
        expected=replacements.get(number,next(p for p in ROOT.glob('*Track*.bin') if int(__import__('re').search(r'Track (\d+)',p.name).group(1))==number))
        assert path==expected.resolve() and path.is_file()
    print('Disc verification: font, UI assets, original ISO entries, both changed tracks and 17 GDI references passed.',flush=True)
    return {'tracks':summaries,'original_files_preserved':len(old),'gdi_references_verified':17}
