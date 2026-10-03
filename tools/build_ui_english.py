"""Build 0.1.11: the four shop/account labels plus the complete English/font patch."""
import argparse
import json
import os
from pathlib import Path

import bizin_font
import font_disc
import shop_account_ui as ui
from build_hd_font import plan as font_plan, validate_font, validate_vq
from build_full_english import validate
from build_vwf import write_track, gdi
from inspect_disc_text import Disc, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    disc = Disc()
    entry = next(e for e in disc.files if e['path'] == '/1ST_READ.BIN')
    original = disc.read(entry['lba'], entry['size'])
    base, report = font_plan(original)
    report['base_font_program_sha256'] = report['target_program_sha256']
    target = ui.account_plan(original, base, report)
    payload, report['font_asset'] = bizin_font.asset(target)
    baseline_payload, _ = bizin_font.asset(base)
    assert payload == baseline_payload, 'Account translation changed font glyph records'
    texture_entry, texture, metadata, before, after = ui.shop_plan(disc)
    report['ui_texture_patches'] = [metadata]
    print(json.dumps({'version': ui.VERSION, 'account_labels': report['account_ui_bindings'],
                      'shop_texture': metadata, 'all_original_793_records_retained': True,
                      'font_asset_identical_to_0_1_10': True}, indent=2, ensure_ascii=True), flush=True)
    if args.validate or args.build:
        report['font_validation'] = validate_font(original, target, report, payload)
        report['font_validation']['bizin'], atlas, metrics = bizin_font.validate(target, report, payload)
        report['font_validation']['vq_bizin_font'] = validate_vq(target, report, atlas, 'Bizin Gothic Bold')
        report['validation'] = validate(original, target, report, metrics)
        report['account_ui_validation'] = ui.validate_account(target, report, metrics)
    if not args.build:
        print('Read-only plan; no test disc written.')
        return
    folder = ROOT / 'work/output' / ('english-' + ui.VERSION)
    folder.mkdir(parents=True, exist_ok=False)
    track = folder / ('Marionette Handler 2 (Japan) (Track 17) English ' + ui.VERSION + '.bin')
    write_track(disc, entry, original, target, track)
    track3, report['font_disc'] = font_disc.embed(disc, payload, folder, track, ui.VERSION)
    font_disc.replace_file(disc, texture_entry, track, texture)
    name = 'Marionette Handler 2 English ' + ui.VERSION
    descriptor = folder / (name + '.gdi')
    gdi(disc, track, descriptor)
    source3 = next(ROOT.glob('*Track 03*.bin'))
    text = descriptor.read_text(encoding='utf-8')
    text = text.replace(Path(os.path.relpath(source3, folder)).as_posix(), track3.name)
    descriptor.write_bytes(text.encode('utf-8'))
    cue = next(ROOT.glob('*.cue')).read_text(encoding='utf-8')
    for source in sorted(ROOT.glob('*Track*.bin')):
        selected = track if '(Track 17)' in source.name else track3 if '(Track 03)' in source.name else source
        cue = cue.replace('"' + source.name + '"', '"' + Path(os.path.relpath(selected, folder)).as_posix() + '"')
    (folder / (name + '.cue')).write_bytes(cue.encode('utf-8'))
    report['disc_validation'] = font_disc.verify(disc, entry, target, track3, track, folder, report)
    for path in (folder / 'PATCH-REPORT.json', ROOT / 'work/ui/english_0.1.11_inventory.json'):
        path.write_bytes((json.dumps(report, indent=2, ensure_ascii=True) + '\n').encode('utf-8'))
    ui.preview(before, after).save(ROOT / 'work/ui/shop-labels-English-0.1.11.png')
    print('Saved test image:', descriptor, flush=True)


if __name__ == '__main__':
    main()
