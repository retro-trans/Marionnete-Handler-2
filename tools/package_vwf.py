"""Stage a local Retro Trans Tools release, defaulting to a read-only plan.

Requires Python 3.12+ and a local Retro Trans Tools checkout. Source/target
tracks stay on disk. The published assets contain only xdelta and metadata.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

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
    source = next(ROOT.glob('*Track 17*.bin'))
    target = next(build_folder.glob('*.bin'))
    config = {'game_id': 'marionette-handler-2' if english else 'marionette-handler-2-vwf',
              'game_name': 'Marionette Handler 2 — ' + label,
              'platform': 'Dreamcast', 'version': version, 'source_commit': commit,
              'patches': [{'patch': 'Marionette-Handler-2-Japan-Track17-' + label + '-' + version + '.xdelta',
                           'edition': 'Japan / Track 17 raw MODE1/2352', 'language': language,
                           'source_version': 'original', 'source_format': 'bin', 'target_format': 'bin',
                           'source': str(source), 'target': str(target)}]}
    output = ROOT / 'work' / 'output' / ('release-' + version)
    print(json.dumps({'config': config, 'output': str(output),
                      'source_sha256': sha256_file(source), 'target_sha256': sha256_file(target)}, indent=2))
    if not args.build:
        print('Dry run only; no release files written.')
        return
    # Tie the manifest to the actual committed tools, rather than uncommitted code.
    if subprocess.check_output(git + ['status', '--porcelain', '--untracked-files=normal'], cwd=str(ROOT), text=True).strip():
        raise ValueError('Commit source changes before packaging the release')
    config_path = build_folder / 'release-local.json'
    if config_path.exists():
        raise ValueError('Local release config already exists')
    config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    build_release(config_path, output, cache=ROOT / 'work' / 'output' / 'engine-cache')
    validate_directory(output)
    print('Retro Trans Tools encode/decode round trip and release validation passed:', output)


if __name__ == '__main__':
    main()
