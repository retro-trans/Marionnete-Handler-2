"""Stage a local Retro Trans Tools release, defaulting to a read-only plan.

Requires Python 3.12+ and a local Retro Trans Tools checkout. Source/target
tracks stay on disk. The published assets contain only xdelta and metadata.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import shutil

from build_vwf import VERSION
from inspect_disc_text import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retro-trans-tools', type=Path, required=True)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--version', default=VERSION)
    parser.add_argument('--language', choices=['ja', 'en'])
    parser.add_argument('--build-prefix', default='vwf', choices=['vwf', 'english'])
    args = parser.parse_args()
    sys.path.insert(0, str(args.retro_trans_tools.resolve()))
    from retro_trans.release import build_release, validate_directory
    from retro_trans.core import sha256_file
    # The Windows sandbox may create Git metadata under a different local SID.
    # Scope trust to this known workspace per command, without global settings.
    git = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]
    commit = subprocess.check_output(git + ['rev-parse', 'HEAD'], cwd=str(ROOT), text=True).strip()
    version = args.version
    english = args.build_prefix == 'english'
    language = args.language or ('en' if english else 'ja')
    if english and language != 'en':
        raise ValueError('English test builds must have language en')
    label = 'English' if english else 'VWF'
    build_folder = ROOT / 'work' / 'output' / (args.build_prefix + '-' + version)
    report_path=build_folder/'PATCH-REPORT.json'
    report=json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    numbers=[3,17] if 'font_disc' in report else [17]
    pairs=[(number,next(ROOT.glob('*Track {:02d}*.bin'.format(number))),
            next(build_folder.glob('*Track {:02d}*.bin'.format(number)))) for number in numbers]
    config = {'game_id': 'marionette-handler-2' if english else 'marionette-handler-2-vwf',
              'game_name': 'Marionette Handler 2 — ' + label,
              'platform': 'Dreamcast', 'version': version, 'source_commit': commit,
              'patches': [{'patch': 'Marionette-Handler-2-Japan-Track'+str(number)+'-' + label + '-' + version + '.xdelta',
                           'edition': 'Japan / Track '+str(number)+' raw MODE1/2352', 'language': language,
                           'source_version': 'original', 'source_format': 'bin', 'target_format': 'bin',
                           'source': str(source), 'target': str(target)} for number,source,target in pairs]}
    output = ROOT / 'work' / 'output' / ('release-' + version)
    print(json.dumps({'config': config, 'output': str(output),
                      'track_hashes': [{'track':number,'source_sha256':sha256_file(source),
                                       'target_sha256':sha256_file(target)} for number,source,target in pairs]}, indent=2))
    if not args.build:
        print('Dry run only; no release files written.')
        return
    # Tie the manifest to the actual committed tools, rather than uncommitted code.
    status=subprocess.check_output(git + ['status', '--porcelain', '--untracked-files=normal'], cwd=str(ROOT), text=True)
    # User-maintained workspace instructions are not a compiled patch input.
    if any(line[3:]!='AGENTS.md' for line in status.splitlines()):
        raise ValueError('Commit source changes before packaging the release')
    config_path = build_folder / 'release-local.json'
    if config_path.exists():
        raise ValueError('Local release config already exists')
    config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    build_release(config_path, output, cache=ROOT / 'work' / 'output' / 'engine-cache')
    if 'font_disc' in report:
        for path in (ROOT/'tools/fonts/bizin-gothic').glob('*LICENSE'):
            shutil.copyfile(path,output/('Bizin-Gothic-'+path.name+'.txt'))
        (output/'README.txt').write_text(
            'Marionette Handler 2 English '+version+'\n\n'
            'Apply BOTH Track 3 and Track 17 patches to the original Japanese raw tracks.\n'
            'Keep all other tracks and the original CUE unchanged. Use the patched tracks\n'
            'under the original filenames in a separate copy of the disc set.\n'
            'Boot the patched disc from scratch; an older save state restores old code.\n'
            'Embedded font: Bizin Gothic Bold v0.0.4. No Flycast texture pack required.\n'
            'https://github.com/yuru7/bizin-gothic\n'
            + ('Includes native shop artwork labels Buy/Sell and account labels Balance/Please wait.\n'
               if report.get('additional_ui_labels') else '') +
            ('Includes narrower spaces, VWF mode 3, and eleven wrapped shop descriptions\n'
             'with a taller native parts-help background.\n'
             if report.get('shop_description_layout') else '') +
            'Native glyph/disc checks passed; Flycast gameplay remains unverified.\n',encoding='utf-8')
        sums=['{}  {}'.format(sha256_file(p),p.name) for p in sorted(output.iterdir()) if p.name!='SHA256SUMS.txt']
        (output/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
    validate_directory(output)
    print('Retro Trans Tools encode/decode round trip and release validation passed:', output)


if __name__ == '__main__':
    main()
